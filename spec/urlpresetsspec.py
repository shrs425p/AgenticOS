from kernel.presets import load_url_presets
import yaml
from unittest.mock import patch

def test_load_url_presets_file(tmp_path):
    preset_file = tmp_path / "presets.yaml"
    preset_file.write_text(yaml.dump([{"name": "test_preset", "url": "https://example.com/test"}]))

    # Custom cfg path
    cfg = {"ops": {"url_presets_path": str(preset_file)}}
    presets = load_url_presets(cfg)
    assert len(presets) == 1
    assert presets[0]["name"] == "test_preset"

def test_load_url_presets_inline():
    with patch('os.path.exists', return_value=False):
        cfg = {"ops": {"url_presets": [{"name": "inline", "url": "url"}]}}
        presets = load_url_presets(cfg)
        assert len(presets) == 1
        assert presets[0]["name"] == "inline"

def test_load_url_presets_dict(tmp_path):
    preset_file = tmp_path / "presets.yaml"
    preset_file.write_text(yaml.dump({"presets": [{"name": "dict_preset", "url": "url"}]}))
    cfg = {"ops": {"url_presets_path": str(preset_file)}}
    presets = load_url_presets(cfg)
    assert len(presets) == 1
    assert presets[0]["name"] == "dict_preset"

def test_load_url_presets_exception(tmp_path):
    preset_file = tmp_path / "presets.yaml"
    preset_file.write_text("invalid: yaml: : :")
    cfg = {"ops": {"url_presets_path": str(preset_file)}}

    # Should catch the yaml parse error and fallback to empty/inline
    assert load_url_presets(cfg) == []
