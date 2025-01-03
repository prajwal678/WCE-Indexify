from kubernetes import client, config
import time

class KubernetesTests:
    def __init__(self):
        config.load_kube_config()
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.autoscaling_v2 = client.AutoscalingV2Api()

    def test_pod_availability(self):
        pods = self.v1.list_namespaced_pod(
            namespace = "default",
            label_selector = "app=web-content-extractor"
        )
        assert len(pods.items) >= 2, "Minimum pod count not maintained" # gpt taught me about assert so ye

    def test_scaling(self):
        initial_pods = self.v1.list_namespaced_pod(
            namespace = "default",
            label_selector = "app=web-content-extractor"
        )
        initial_count = len(initial_pods.items)
        asyncio.run(main())
        time.sleep(60)

        current_pods = self.v1.list_namespaced_pod(
            namespace = "default",
            label_selector = "app=web-content-extractor"
        )
        assert len(current_pods.items) > initial_count, "Autoscaling did not increase pod count"

    def test_recovery(self):
        pods = self.v1.list_namespaced_pod(
            namespace = "default",
            label_selector = "app=web-content-extractor"
        )
        # we kill to cehck how it recovers
        self.v1.delete_namespaced_pod(
            name = pods.items[0].metadata.name,
            namespace = "default"
        )

        time.sleep(30)
        new_pods = self.v1.list_namespaced_pod(
            namespace = "default",
            label_selector = "app=web-content-extractor"
        )
        assert len(new_pods.items) == len(pods.items), "Failed to recover from pod deletion"

if __name__ == "__main__":
    k8s_tests = KubernetesTests()
    k8s_tests.test_pod_availability()
    k8s_tests.test_scaling()
    k8s_tests.test_recovery()