from feature_modelnet_minio import ModelNetMinioLayoutsTest
class StrictMatrix(ModelNetMinioLayoutsTest):
    def set_test_params(self):super().set_test_params()
    def run_test(self):super().run_test()
    def _start_container(self):
        endpoint=super()._start_container();assert endpoint,self.not_run;return endpoint
if __name__=='__main__':StrictMatrix(__file__).main()
