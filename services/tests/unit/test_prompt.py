"""单元测试（V 模型左下 → 单元测试，对应 REQ-101）"""
import pytest
from app import load_prompt, list_versions


def test_load_prompt_v1():
    """REQ-101: prompt 加载"""
    p = load_prompt("v1")
    assert "AI 助手" in p or "assistant" in p.lower()


def test_load_prompt_v2():
    """REQ-101: prompt v2 加载"""
    p = load_prompt("v2")
    assert "AI 助手" in p or "assistant" in p.lower()


def test_load_prompt_invalid_version():
    """REQ-101: 不存在的版本应该报错"""
    with pytest.raises(Exception):  # HTTPException 或 KeyError
        load_prompt("v999")


def test_list_versions():
    """REQ-101: 列版本"""
    versions = list_versions()
    assert "v1" in versions
    assert "v2" in versions


def test_prompt_template_not_empty():
    """REQ-101: template 不能空"""
    for v in list_versions():
        p = load_prompt(v)
        assert p.strip(), f"version {v} template is empty"