"""
Shared test data constants (sample logs, expected outputs).
Import this from any test file: from tests.fixtures import SAMPLE_K8S_LOG
"""

SAMPLE_K8S_LOG = """\
2025-01-15T09:00:01Z kubelet[1234]: E0115 09:00:01.123456 1234 pod_workers.go:190] Error syncing pod
2025-01-15T09:00:02Z kubelet[1234]: W0115 09:00:02.234567 1234 event.go:268] CrashLoopBackOff
2025-01-15T09:00:03Z kubelet[1234]: E0115 09:00:03.345678 1234 pod_workers.go:190] OOMKilled: container exceeded memory limit 256Mi
2025-01-15T09:00:04Z kube-apiserver: Error: ImagePullBackOff for image nginx:latest\
""".strip()

SAMPLE_NGINX_LOG = """\
2025-01-15 10:00:01 [error] 1234#1234: *999 upstream timed out (110: Connection timed out)
2025-01-15 10:00:02 [error] 1234#1234: *1000 connect() failed (111: Connection refused) while connecting to upstream
2025-01-15 10:00:03 nginx: 502 Bad Gateway — upstream service unreachable\
""".strip()

SAMPLE_MIXED_LOG = """\
2025-01-15T08:00:00Z ERROR payment-service: Connection refused to redis:6379
2025-01-15T08:00:01Z ERROR payment-service: NOAUTH Authentication required
2025-01-15T08:00:05Z ERROR postgres: FATAL: remaining connection slots are reserved
2025-01-15T08:00:10Z kubelet: CrashLoopBackOff — payment-processor
2025-01-15T08:00:15Z ERROR nginx: 502 Bad Gateway upstream payment-service\
""".strip()

SAMPLE_APP_LOG = """\
2025-01-15T11:00:00Z ERROR app: Traceback (most recent call last):
  File "payment.py", line 45, in process_payment
    raise ConnectionError("Database unreachable")
ConnectionError: Database unreachable\
""".strip()
