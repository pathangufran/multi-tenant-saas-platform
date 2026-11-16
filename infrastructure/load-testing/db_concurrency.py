import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import psycopg

DATABASE_URL = os.environ["DATABASE_URL"]

WORKERS = 50
QUERIES_PER_WORKER = 20

results = []
lock = threading.Lock()

def execute_queries(worker_id):
    
    successful = 0
    failed = 0
    
    started = time.perf_counter()
    
    try:
        with psycopg.connect(
            DATABASE_URL,
            connect_timeout=10,
        ) as connection:
            
            with connection.cursor() as cursor:
                
                for _ in range(QUERIES_PER_WORKER):
                    try:
                        cursor.execute(
                            "SELECT pg_sleep(0.01)"
                        )

                        cursor.fetchone()
                        successful += 1

                    except Exception:
                        failed += 1

    except Exception as exc:
        failed += QUERIES_PER_WORKER

        print(
            f"Worker {worker_id} connection error: {exc}"
        )

    duration = time.perf_counter() - started
    
    with lock:
        results.append({
            "worker": worker_id,
            "successful": successful,
            "failed": failed,
            "duration": duration,
        })

def main():
    
    started = time.perf_counter()
    
    with ThreadPoolExecutor(
        max_workers=WORKERS
    ) as executor:
        
        list(
            executor.map(
                execute_queries,
                range(WORKERS),
            )
        )
        
    total_duration = time.perf_counter() - started
    
    successful = sum(
        result["successful"]
        for result in results
    )

    failed = sum(
        result["failed"]
        for result in results
    )

    print("Total workers:", WORKERS)
    print("Successful queries:", successful)
    print("Failed queries:", failed)
    print("Total duration:", round(total_duration, 2))

    if results:
        print(
            "Slowest worker:",
            round(
                max(r["duration"] for r in results),
                2,
            ),
        )

if __name__ == "__main__":
    main()