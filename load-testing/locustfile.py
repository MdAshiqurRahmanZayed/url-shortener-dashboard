"""
Locust load test — simulates 12 PM traffic spike for URL Shortener platform.

Run:
  # Interactive UI
  locust -f locustfile.py --host http://urlshortener.local

  # Headless (CI mode) — spike scenario
  locust -f locustfile.py \
    --host http://urlshortener.local \
    --users 200 \
    --spawn-rate 20 \
    --run-time 5m \
    --headless \
    --html report.html
"""

import random
import string
from locust import HttpUser, task, between, events


def random_url():
    domains = ["github.com", "stackoverflow.com", "python.org", "kubernetes.io", "docs.docker.com"]
    paths = ["".join(random.choices(string.ascii_lowercase, k=8)) for _ in range(3)]
    return f"https://{random.choice(domains)}/{'/'.join(paths)}"


SHORT_CODES = []


class DashboardUser(HttpUser):
    """Simulates a user browsing the dashboard — lighter load."""

    wait_time = between(2, 5)
    weight = 2

    @task(3)
    def view_dashboard(self):
        self.client.get("/", name="Dashboard")

    @task(1)
    def view_stats(self):
        self.client.get("/api/stats", name="Stats API")


class ActiveUser(HttpUser):
    """Simulates an employee actively shortening and clicking URLs at 12 PM."""

    wait_time = between(1, 3)
    weight = 5

    @task(4)
    def shorten_url(self):
        long_url = random_url()
        with self.client.post(
            "/create",
            data={"long_url": long_url},
            name="Shorten URL",
            allow_redirects=False,
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 302, 303):
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(3)
    def shorten_via_api(self):
        with self.client.post(
            "/go/api/shorten",
            json={"long_url": random_url()},
            name="Go API Shorten",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                if "short_code" in data:
                    SHORT_CODES.append(data["short_code"])
                resp.success()
            else:
                resp.failure(f"Status: {resp.status_code}")

    @task(2)
    def follow_short_url(self):
        if not SHORT_CODES:
            return
        code = random.choice(SHORT_CODES)
        self.client.get(
            f"/go/{code}",
            name="Follow Short URL",
            allow_redirects=False,
        )

    @task(1)
    def view_dashboard(self):
        self.client.get("/", name="Dashboard")


class HeavyUser(HttpUser):
    """Simulates burst traffic at peak — no wait between requests."""

    wait_time = between(0.1, 0.5)
    weight = 1

    @task(5)
    def rapid_shorten(self):
        self.client.post(
            "/go/api/shorten",
            json={"long_url": random_url()},
            name="Rapid Shorten",
        )

    @task(2)
    def rapid_stats(self):
        self.client.get("/api/stats", name="Rapid Stats")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("Load test started — simulating 12 PM traffic spike")
    print(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("Load test complete")
    stats = environment.stats.total
    print(f"Total requests:  {stats.num_requests}")
    print(f"Failed requests: {stats.num_failures}")
    print(f"Avg response:    {stats.avg_response_time:.0f}ms")
    print(f"95th percentile: {stats.get_response_time_percentile(0.95):.0f}ms")
    print(f"RPS:             {stats.current_rps:.1f}")
