"""Bounded controlled HTTP origin for the real S3 client completion probe.

This is a simulated origin, not FakeS3, AWS or MinIO. It observes signed request
headers but does not validate SigV4; authentication is not the property tested.
"""
from contextlib import AbstractContextManager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import re
import threading
import time
from urllib.parse import parse_qs, unquote, urlsplit
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

MAX_BODY = 20 * 1024 * 1024 - 1
MAX_RETAINED = 64 * 1024 * 1024
MODES = {'success', 'error200', 'error500'}


class Origin(AbstractContextManager):
    def __init__(self, mode='success', deadline_seconds=120):
        if mode not in MODES:
            raise ValueError('unsupported completion mode')
        if not 0 < deadline_seconds <= 120:
            raise ValueError('deadline must be at most120s')
        self.mode = mode
        self.completion_modes = []
        self._deadline_seconds = deadline_seconds
        self._lock = threading.RLock()
        self._objects = {}
        self._uploads = {}
        self._requests = []
        self._aborts = []
        self._next_id = 1
        self._started = None
        self._server = None
        self._thread = None

    def __enter__(self):
        if self._server is not None:
            raise RuntimeError('origin already active')
        self._started = time.monotonic()
        self._server = ThreadingHTTPServer(('127.0.0.1', 0), self._handler())
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        kwargs={'poll_interval': .05}, daemon=True)
        self._thread.start()
        self.endpoint = 'http://127.0.0.1:' + str(self._server.server_port)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                raise RuntimeError('origin thread did not stop')
            self._server = None
        return False

    def _retained(self):
        return sum(map(len, self._objects.values())) + sum(
            len(data) for upload in self._uploads.values()
            for data in upload['parts'].values())

    def object_bytes(self, path):
        with self._lock:
            return self._objects.get('/' + path.lstrip('/'))

    def snapshot(self):
        with self._lock:
            return {
                'origin': 'controlled local HTTP response fixture; not AWS/MinIO/FakeS3',
                'sigv4_validation': False,
                'mode': self.mode,
                'retained_bytes': self._retained(),
                'objects': {key: {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}
                            for key, value in sorted(self._objects.items())},
                'uploads': {uid: {'path': value['path'],
                                  'parts': {str(part): {'bytes': len(data),
                                             'sha256': hashlib.sha256(data).hexdigest()}
                                            for part, data in sorted(value['parts'].items())}}
                            for uid, value in sorted(self._uploads.items())},
                'aborted_uploads': list(self._aborts),
                'requests': [dict(row) for row in self._requests],
            }

    def _handler(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.0'
            server_version = 'BoundedCompletionOrigin/1'
            sys_version = ''

            def log_message(self, *_):
                pass

            def setup(self):
                super().setup()
                self.connection.settimeout(10)

            def _reply(self, code, body=b'', etag=None, content_type='application/xml', head=False):
                self.send_response(code)
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Content-Type', content_type)
                self.send_header('Connection', 'close')
                if etag is not None:
                    self.send_header('ETag', '"' + etag + '"')
                self.end_headers()
                if not head and body:
                    self.wfile.write(body)
                self.close_connection = True

            def _serve(self):
                row = None
                try:
                    parsed = urlsplit(self.path)
                    path = unquote(parsed.path)
                    query = parse_qs(parsed.query, keep_blank_values=True)
                    authorization = self.headers.get('Authorization', '')
                    scope = re.search(r'Credential=[^/\s,]+/([^,\s]+)', authorization)
                    length = int(self.headers.get('Content-Length', '0'))
                    if length < 0 or length > MAX_BODY or self.headers.get('Transfer-Encoding'):
                        self._reply(413, b'<Error><Code>EntityTooLarge</Code></Error>')
                        return
                    if time.monotonic() - owner._started >= owner._deadline_seconds:
                        self._reply(503, b'<Error><Code>FixtureDeadline</Code></Error>')
                        return
                    body = self.rfile.read(length) if length else b''
                    if len(body) != length:
                        self._reply(400, b'<Error><Code>IncompleteBody</Code></Error>')
                        return
                    row = {'method': self.command, 'path': path, 'query': query,
                           'request_bytes': length,
                           'authorization_present': bool(authorization),
                           'sigv4_scheme': authorization.startswith('AWS4-HMAC-SHA256 '),
                           'credential_scope': scope.group(1) if scope else None,
                           'amz_date_present': bool(self.headers.get('x-amz-date'))}
                    with owner._lock:
                        if len(owner._requests) >= 64:
                            raise RuntimeError('request-count bound exceeded')
                        owner._requests.append(row)
                        code, response, etag, kind = self._dispatch(path, query, body)
                        row.update(response_status=code, response_kind=kind,
                                   object_exists_after=path in owner._objects,
                                   object_sha256_after=(hashlib.sha256(owner._objects[path]).hexdigest() if path in owner._objects else None),
                                   upload_count_after=len(owner._uploads))
                        row.setdefault('completion_mode', owner.mode)
                    self._reply(code, response, etag=etag, head=self.command == 'HEAD')
                except Exception as exc:
                    if row is not None:
                        row.update(response_status=500, fixture_error=type(exc).__name__)
                    self._reply(500, b'<Error><Code>FixtureFailure</Code></Error>')

            def _dispatch(self, path, query, body):
                uid = query.get('uploadId', [None])[0]
                if self.command == 'POST' and 'uploads' in query:
                    uid = 'probe-upload-' + str(owner._next_id)
                    owner._next_id += 1
                    owner._uploads[uid] = {'path': path, 'parts': {}}
                    bucket, _, key = path.lstrip('/').partition('/')
                    response = ('<InitiateMultipartUploadResult><Bucket>' + escape(bucket) + '</Bucket>'
                                '<Key>' + escape(key) + '</Key><UploadId>' + uid + '</UploadId>'
                                '</InitiateMultipartUploadResult>').encode()
                    return 200, response, None, 'multipart-begin'
                if uid is not None:
                    upload = owner._uploads.get(uid)
                    if upload is None or upload['path'] != path:
                        return 404, b'<Error><Code>NoSuchUpload</Code></Error>', None, 'no-upload'
                    if self.command == 'PUT' and 'partNumber' in query:
                        part = int(query['partNumber'][0])
                        if not 1 <= part <= 10000:
                            return 400, b'<Error><Code>InvalidPart</Code></Error>', None, 'invalid-part'
                        previous = upload['parts'].get(part, b'')
                        if owner._retained() - len(previous) + len(body) > MAX_RETAINED:
                            raise RuntimeError('retained-data bound exceeded')
                        upload['parts'][part] = body
                        return 200, b'', hashlib.md5(body).hexdigest(), 'multipart-part'
                    if self.command == 'DELETE':
                        owner._aborts.append(uid)
                        del owner._uploads[uid]
                        return 204, b'', None, 'multipart-abort'
                    if self.command == 'POST':
                        mode = owner.completion_modes.pop(0) if owner.completion_modes else owner.mode
                        if mode not in MODES:
                            raise RuntimeError('invalid completion mode')
                        owner._requests[-1]['completion_mode'] = mode
                        # Verify the real client's supplied ordered part/ETag list.
                        root = ET.fromstring(body)
                        requested = []
                        for part in root.findall('Part'):
                            number = int(part.findtext('PartNumber'))
                            tag = (part.findtext('ETag') or '').strip('"')
                            if number not in upload['parts'] or tag != hashlib.md5(upload['parts'][number]).hexdigest():
                                return 400, b'<Error><Code>InvalidPart</Code></Error>', None, 'invalid-completion-parts'
                            requested.append(number)
                        if requested != sorted(upload['parts']) or not requested:
                            return 400, b'<Error><Code>InvalidPartOrder</Code></Error>', None, 'invalid-completion-order'
                        if mode in ('error200', 'error500'):
                            # Whitespace is allowed before S3's eventual response body.
                            response = (b' \n<?xml version="1.0" encoding="UTF-8"?>'
                                        b'<Error><Code>InternalError</Code>'
                                        b'<Message>Controlled completion failure</Message></Error>')
                            return (200 if mode == 'error200' else 500), response, None, 'multipart-error'
                        data = b''.join(upload['parts'][part] for part in requested)
                        # Removing staged parts before keeping the finalized bytes keeps
                        # the steady-state retained-data cap independent of part count.
                        old = owner._objects.get(path, b'')
                        if owner._retained() - sum(map(len, upload['parts'].values())) - len(old) + len(data) > MAX_RETAINED:
                            raise RuntimeError('retained-data bound exceeded')
                        owner._objects[path] = data
                        del owner._uploads[uid]
                        bucket, _, key = path.lstrip('/').partition('/')
                        response = ('<?xml version="1.0" encoding="UTF-8"?>'
                                    '<CompleteMultipartUploadResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
                                    '<Location>' + escape(owner.endpoint + urlsplit(self.path).path) + '</Location>'
                                    '<Bucket>' + escape(bucket) + '</Bucket><Key>' + escape(key) + '</Key><ETag>"' + hashlib.md5(data).hexdigest() + '"</ETag>'
                                    '</CompleteMultipartUploadResult>').encode()
                        return 200, response, None, 'multipart-success'
                if self.command == 'PUT' and uid is None:
                    previous = owner._objects.get(path, b'')
                    if owner._retained() - len(previous) + len(body) > MAX_RETAINED:
                        raise RuntimeError('retained-data bound exceeded')
                    owner._objects[path] = body
                    return 200, b'', hashlib.md5(body).hexdigest(), 'ordinary-put'
                if self.command in ('GET', 'HEAD'):
                    data = owner._objects.get(path)
                    if data is None:
                        return 404, b'<Error><Code>NoSuchKey</Code></Error>', None, 'missing-object'
                    return 200, data, hashlib.md5(data).hexdigest(), 'object-read'
                return 400, b'<Error><Code>UnsupportedFixtureOperation</Code></Error>', None, 'unsupported'

            do_POST = _serve
            do_PUT = _serve
            do_DELETE = _serve
            do_GET = _serve
            do_HEAD = _serve

        return Handler
