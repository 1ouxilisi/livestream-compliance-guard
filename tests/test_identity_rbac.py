# -*- coding: utf-8 -*-
"""RBAC 角色动作矩阵：只读 / 改写 / 管理三级权限与工具动作映射。"""
import pytest

from lcg.identity import (
    ACTION_ADMIN,
    ACTION_READ,
    ACTION_WRITE,
    ROLE_ADMIN,
    ROLE_OPERATOR,
    ROLE_VIEWER,
    action_for_tool,
    actions_for_role,
    can,
    require_permission,
)


def test_role_action_matrix():
    assert actions_for_role(ROLE_VIEWER) == frozenset({ACTION_READ})
    assert actions_for_role(ROLE_OPERATOR) == frozenset({ACTION_READ, ACTION_WRITE})
    assert actions_for_role(ROLE_ADMIN) == frozenset(
        {ACTION_READ, ACTION_WRITE, ACTION_ADMIN})


def test_can_per_role():
    # viewer：只读
    assert can(ROLE_VIEWER, ACTION_READ) is True
    assert can(ROLE_VIEWER, ACTION_WRITE) is False
    assert can(ROLE_VIEWER, ACTION_ADMIN) is False
    # operator：读写，不能管理
    assert can(ROLE_OPERATOR, ACTION_READ) is True
    assert can(ROLE_OPERATOR, ACTION_WRITE) is True
    assert can(ROLE_OPERATOR, ACTION_ADMIN) is False
    # admin：全部
    assert can(ROLE_ADMIN, ACTION_ADMIN) is True


def test_can_rejects_unknown_role_or_action():
    with pytest.raises(ValueError):
        can("superuser", ACTION_READ)
    with pytest.raises(ValueError):
        can(ROLE_VIEWER, "delete")


def test_require_permission_allows_and_blocks():
    # 放行不抛异常
    require_permission(ROLE_OPERATOR, ACTION_WRITE)
    require_permission(ROLE_ADMIN, ACTION_ADMIN)
    # 越权抛 PermissionError
    with pytest.raises(PermissionError):
        require_permission(ROLE_VIEWER, ACTION_WRITE)
    with pytest.raises(PermissionError):
        require_permission(ROLE_OPERATOR, ACTION_ADMIN)


def test_require_permission_empty_role_passes_through():
    # 未启用鉴权（角色为空）时守卫放行，不阻断 stdio / 开放内网路径
    require_permission("", ACTION_WRITE)
    require_permission("", ACTION_ADMIN)


def test_tool_action_mapping():
    read_tools = {"scan_text", "scan_livestream", "compliance_rules", "scan_smart"}
    write_tools = {"safe_rewrite", "rewrite_smart"}
    for name in read_tools:
        assert action_for_tool(name) == ACTION_READ
    for name in write_tools:
        assert action_for_tool(name) == ACTION_WRITE


def test_unknown_tool_rejected():
    with pytest.raises(ValueError):
        action_for_tool("drop_database")
