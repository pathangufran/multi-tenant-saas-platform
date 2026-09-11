def test_request_id_is_generated(client):
    response = client.get("/health/")

    assert response.status_code == 200
    assert response["X-Request-ID"]


def test_request_id_is_preserved(client):
    request_id = "test-request-123"

    response = client.get(
        "/health/",
        HTTP_X_REQUEST_ID=request_id,
    )

    assert response.status_code == 200
    assert response["X-Request-ID"] == request_id