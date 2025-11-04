from toml_schema import validate_file

validate_file("config.toml", "schema.toml")
print("✅ TOML is valid.")
