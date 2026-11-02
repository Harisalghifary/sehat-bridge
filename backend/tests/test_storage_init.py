from app.init_storage import cors_rules


def test_cors_rules_allow_the_site_origin() -> None:
    rules = cors_rules("http://localhost:8080")["CORSRules"]
    assert len(rules) == 1
    rule = rules[0]
    assert rule["AllowedOrigins"] == ["http://localhost:8080"]
    assert "POST" in rule["AllowedMethods"]
    assert "ETag" in rule["ExposeHeaders"]
    assert rule["AllowedHeaders"] == ["*"]
