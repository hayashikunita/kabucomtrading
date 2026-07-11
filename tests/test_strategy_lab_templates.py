"""Strategy Lab テンプレート定義の整合性テスト。"""

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
STRATEGY_LAB = ROOT / "strategy_lab.py"


def _load_template_nodes():
    source = STRATEGY_LAB.read_text(encoding="utf-8")
    module = ast.parse(source)
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "STRATEGY_TEMPLATES":
                    return ast.literal_eval(node.value)
    raise AssertionError("STRATEGY_TEMPLATES が見つかりません")


def _load_sample_params_nodes():
    source = STRATEGY_LAB.read_text(encoding="utf-8")
    module = ast.parse(source)
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "TEMPLATE_SAMPLE_PARAMS":
                    return ast.literal_eval(node.value)
    raise AssertionError("TEMPLATE_SAMPLE_PARAMS が見つかりません")


def _optimize_param_names(optimize_spec: str):
    names = []
    for raw in optimize_spec.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        name, _ = line.split("=", 1)
        names.append(name.strip())
    return set(names)


def test_all_templates_have_code_and_optimize_spec():
    templates = _load_template_nodes()

    assert templates, "テンプレートが空です"
    for name, template in templates.items():
        assert isinstance(template, dict), f"{name} は dict 形式である必要があります"
        assert "code" in template, f"{name} に code がありません"
        assert "optimize_spec" in template, f"{name} に optimize_spec がありません"
        assert isinstance(template["code"], str) and template["code"].strip(), f"{name} の code が空です"
        assert isinstance(template["optimize_spec"], str) and template["optimize_spec"].strip(), (
            f"{name} の optimize_spec が空です"
        )


def test_all_templates_are_params_compatible():
    templates = _load_template_nodes()

    for name, template in templates.items():
        code = template["code"]
        assert "def strategy(ctx, params):" in code, f"{name} が params 対応していません"


def test_optimize_spec_lines_match_params_style():
    templates = _load_template_nodes()

    for name, template in templates.items():
        lines = [line.strip() for line in template["optimize_spec"].splitlines() if line.strip()]
        assert lines, f"{name} の optimize_spec に有効行がありません"
        for line in lines:
            assert "=" in line, f"{name} の optimize_spec 行が不正です: {line}"


def test_all_templates_have_fixed_sample_params():
    templates = _load_template_nodes()
    sample_params = _load_sample_params_nodes()

    assert sample_params, "TEMPLATE_SAMPLE_PARAMS が空です"
    assert set(sample_params.keys()) == set(templates.keys()), (
        "TEMPLATE_SAMPLE_PARAMS のキーが STRATEGY_TEMPLATES と一致していません"
    )


def test_sample_params_keys_match_optimize_spec_names():
    templates = _load_template_nodes()
    sample_params = _load_sample_params_nodes()

    for name, template in templates.items():
        optimize_names = _optimize_param_names(template["optimize_spec"])
        sample = sample_params[name]

        assert isinstance(sample, dict), f"{name} の sample_params は dict 形式である必要があります"
        assert sample, f"{name} の sample_params が空です"
        assert set(sample.keys()).issubset(optimize_names), (
            f"{name} の sample_params キーが optimize_spec と不一致です: {set(sample.keys()) - optimize_names}"
        )


def test_sample_params_are_json_serializable():
    sample_params = _load_sample_params_nodes()

    for name, sample in sample_params.items():
        try:
            dumped = json.dumps(sample, ensure_ascii=False)
            loaded = json.loads(dumped)
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(f"{name} の sample_params はJSON化できません: {exc}") from exc

        assert isinstance(loaded, dict), f"{name} の sample_params はJSONオブジェクトである必要があります"
