"""Public synthetic presentation inputs; no actual model, signature or key."""
PROFILE_ID = 'ab' * 48
MODEL_ID = 'cd' * 48
BINDING = {'architecture': 'BTXTinyLM', 'layers': 2, 'intermediate_size': 32,
           'hidden_size': 16, 'heads': 2, 'activation': 'gelu',
           'adapter': 'CONTROLLED_GUI_FIXTURE', 'weights_hash': 'ef' * 48,
           'execution_fingerprint': 'GUI_ONLY_NOT_SCIENTIFIC'}
OPERATIONS = [
    {'id': 'fixture-op-' + str(i), 'kind': 'neuron_scale', 'layer': i % 2,
     'indices': [i, i + 1], 'coefficient_ppm': 500000, 'normalization': 'absolute',
     'phase': 'both', 'token_start': 0, 'token_end': -1, 'tensor': None,
     'calibration': None, 'bounds_ppm': None, 'sae': None}
    for i in range(20)
]
SUMMARY = {'id': PROFILE_ID, 'title': 'CONTROLLED 905 dialog fixture',
           'publisher': 'SYNTHETIC_NO_SIGNATURE', 'trust': 'CONTROLLED_UI_DATA'}
MODEL = {'id': MODEL_ID, 'binding': BINDING}
PROFILE = {'summary': SUMMARY, 'profile': {
    'binding': BINDING, 'title': SUMMARY['title'], 'description': 'UI-only fixture',
    'operations': OPERATIONS, 'training_recipe': {}, 'privacy': 'private',
    'license': 'TEST_ONLY', 'claims': [], 'parent_profiles': []}, 'editable_tensors': {}}
