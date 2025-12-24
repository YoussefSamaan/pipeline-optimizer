from app.core.errors import DomainError
from app import main


class TestMain:
    def test_health_check(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_domain_error_handler_returns_400(self, client):
        """
        Ensures DomainError is converted into a 400 response
        with a stable JSON payload.
        """

        # Add a test-only route to trigger the exception
        app = client.app

        @app.get("/_test/domain-error")
        def _raise_domain_error():
            raise DomainError("boom")

        r = client.get("/_test/domain-error")
        assert r.status_code == 400
        assert r.json() == {"detail": "boom"}

    def test_openapi_contains_v1_routes(self, client):
        """
        Ensures the v1 router is actually mounted.
        """
        r = client.get("/openapi.json")
        assert r.status_code == 200

        schema = r.json()
        assert any(path.startswith("/v1/") for path in schema["paths"])

    def test_openapi_metadata(self, client):
        """
        Guards against accidental API metadata regressions.
        """
        r = client.get("/openapi.json")
        schema = r.json()

        assert schema["info"]["title"] == "Pipeline Optimizer API"
        assert schema["info"]["version"] == "0.1.0"

    def test_run_uses_default_env(self, monkeypatch):
        calls = {}

        def fake_run(app_str, host, port, reload):
            calls["app_str"] = app_str
            calls["host"] = host
            calls["port"] = port
            calls["reload"] = reload

        # Patch uvicorn.run that is imported inside main.run()
        monkeypatch.setattr("uvicorn.run", fake_run, raising=True)

        # Ensure env vars are not set
        monkeypatch.delenv("PORT", raising=False)
        monkeypatch.delenv("RELOAD", raising=False)

        main.run()

        assert calls == {
            "app_str": "app.main:app",
            "host": "0.0.0.0",
            "port": 8000,
            "reload": False,
        }

    def test_run_reads_env_vars(self, monkeypatch):
        calls = {}

        def fake_run(app_str, host, port, reload):
            calls["app_str"] = app_str
            calls["host"] = host
            calls["port"] = port
            calls["reload"] = reload

        monkeypatch.setattr("uvicorn.run", fake_run, raising=True)

        monkeypatch.setenv("PORT", "1234")
        monkeypatch.setenv("RELOAD", "true")

        main.run()

        assert calls["port"] == 1234
        assert calls["reload"] is True
