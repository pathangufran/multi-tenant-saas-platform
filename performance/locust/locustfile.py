import os
import random
from pathlib import Path
from dotenv import load_dotenv
from locust import HttpUser, between, task

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

def env(name, default=""):
    
    return os.getenv(name,default).strip()

AUTH_BASE_URL = env(
    "AUTH_BASE_URL",
    "http://localhost:8000",
)
AUTH_LOGIN_PATH = env(
    "AUTH_LOGIN_PATH",
    "/api/v1/auth/login/",
)

AUTH_USERNAME = env("AUTH_USERNAME")
AUTH_PASSWORD = env("AUTH_PASSWORD")

ACCESS_TOKEN_FIELD = env(
    "ACCESS_TOKEN_FIELD",
    "access",
)
REFRESH_TOKEN_FIELD = env(
    "REFRESH_TOKEN_FIELD",
    "refresh",
)
REQUEST_TIMEOUT = float(
    env("REQUEST_TIMEOUT", "10")
)
MIN_WAIT = float(
    env("MIN_WAIT_SECONDS", "1")
)
MAX_WAIT = float(
    env("MAX_WAIT_SECONDS", "3")
)

class SaaSBaseUser(HttpUser):
    
    abstract = True
    wait_time = between(MIN_WAIT,MAX_WAIT)
    
    read_endpoints = []
    write_endpoints = []
    
    def on_start(self):
        self.access_token = None
        self.refresh_token = None
        
        self.authenticate()
        
    def authenticate(self):
        if not AUTH_USERNAME or not AUTH_PASSWORD:
            self.environment.runner.quit()
            raise RuntimeError(
                "AUTH_USERNAME and AUTH_PASSWORD "
                "must be configured."
            )
            
        try:
            response = self.client.post(
                f"{AUTH_BASE_URL}{AUTH_LOGIN_PATH}",
                json={
                    "email": AUTH_USERNAME,
                    "password": AUTH_PASSWORD,
                },
                name="AUTH / login",
                timeout=REQUEST_TIMEOUT,
            )
            if response.status_code not in (200,201):
                self.environment.runner.quit()
                raise RuntimeError(
                    f"Login failed: HTTP {response.status_code}"
                )
                
            data = response.json()
    
            self.access_token = data.get(ACCESS_TOKEN_FIELD)
            self.refresh_token = data.get(REFRESH_TOKEN_FIELD)
            
            if not self.access_token:
                self.environment.runner.quit()
                raise RuntimeError(
                    "Access token not found in login response."
                )
                
            self.client.headers.update({
                "Authorization": (
                    f"Bearer {self.access_token}"
                )
            })
            
        except (ValueError, TypeError) as exc:
            self.environment.runner.quit()
            raise RuntimeError(
                "Invalid authentication response."
            ) from exc
            
    def call_read_endpoint(self):
        if not self.read_endpoints:
            return
        
        path = random.choice(self.read_endpoints)
        
        if not path:
            return 
        
        self.client.get(
            path,
            name=f"READ {path}",
            timeout=REQUEST_TIMEOUT,
        )
        
    def call_write_endpoint(self):
        if not self.write_endpoints:
            return 
        
        path,payload = random.choice(
            self.write_endpoints
        )
        
        if not path:
            return 
        
        self.client.post(
            path,
            json=payload,
            name=f"WRITE {path}",
            timeout=REQUEST_TIMEOUT,
        )
        
    @task(5)
    def read_operations(self):
        self.call_read_endpoint()
        
    @task(1)
    def write_operations(self):
        self.call_write_endpoint()
        
class AuthUser(SaaSBaseUser):
    weight = 15
    host = AUTH_BASE_URL

    def on_start(self):
        self.access_token = None
        self.refresh_token = None
        self.authenticate()

    @task(5)
    def refresh_token_operation(self):
        refresh_path = env("AUTH_REFRESH_PATH")

        if not refresh_path or not self.refresh_token:
            return

        response = self.client.post(
            refresh_path,
            json={"refresh": self.refresh_token},
            name="AUTH / refresh",
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code == 200:
            data = response.json()
            new_access = data.get(
                ACCESS_TOKEN_FIELD
            )

            if new_access:
                self.access_token = new_access
                self.client.headers.update({
                    "Authorization": (
                        f"Bearer {new_access}"
                    )
                })

class TenantUser(SaaSBaseUser):
    weight = 10
    
    host = env(
        "TENANT_BASE_URL",
        "http://localhost:8001",
    )

    read_endpoints = [
        env("TENANT_LIST_PATH"),
        env("TENANT_DETAIL_PATH"),
    ]

class CoreUser(SaaSBaseUser):
    weight = 45
    
    host = env(
        "CORE_BASE_URL",
        "http://localhost:8002",
    )

    read_endpoints = [
        env("CORE_PROJECT_LIST_PATH"),
        env("CORE_TASK_LIST_PATH"),
        env("CORE_TEAM_LIST_PATH"),
        env("CORE_COMMENT_LIST_PATH"),
    ]

    write_endpoints = [
        (
            env("CORE_TASK_CREATE_PATH"),
            {
                "title": "Locust performance test task",
                "description": "Generated test workload",
            },
        ),
    ]

class BillingUser(SaaSBaseUser):
    weight = 10
    
    host = env(
        "BILLING_BASE_URL",
        "http://localhost:8004",
    )

    read_endpoints = [
        env("BILLING_PLAN_LIST_PATH"),
        env("BILLING_SUBSCRIPTION_LIST_PATH"),
        env("BILLING_INVOICE_LIST_PATH"),
    ]

class NotificationUser(SaaSBaseUser):
    weight = 20
    
    host = env(
        "NOTIFICATION_BASE_URL",
        "http://localhost:8003",
    )

    read_endpoints = [
        env("NOTIFICATION_LIST_PATH"),
        env("NOTIFICATION_UNREAD_COUNT_PATH"),
    ]
