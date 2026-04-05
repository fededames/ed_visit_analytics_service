from pathlib import Path


def test_env_example_points_local_debug_to_docker_postgres_port():
    env_example = Path(__file__).resolve().parents[2] / ".env.example"
    content = env_example.read_text(encoding="utf-8")
    assert "localhost:55432" in content
    assert "postgresql+psycopg://postgres:postgres@" in content


def test_docker_compose_publishes_postgres_on_local_debug_port():
    compose_file = Path(__file__).resolve().parents[2] / "docker-compose.yml"
    content = compose_file.read_text(encoding="utf-8")
    assert '"55432:5432"' in content
