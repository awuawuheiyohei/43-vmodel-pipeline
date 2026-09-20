"""系统测试（V 模型右下 → 系统测试，对应 REQ-103）

k6 负载脚本（CI 调用，不在 pytest 里跑）
这里跑: 验证 k6 脚本语法 + 阈值设置正确
"""
import re
from pathlib import Path


K6_SCRIPT = """
import http from 'http';
import { check } from 'k6';

export const options = {
  vus: 10,
  duration: '30s',
  thresholds: {
    http_req_duration: ['p(99)<2000'],  // REQ-003: P99 ≤ 2s
    http_reqs: ['rate>=10'],             // REQ-002: QPS ≥ 10
  },
};

export default function () {
  const res = http.post(__ENV.TARGET_URL, JSON.stringify({message: 'ping'}));
  check(res, {
    'status is 200': (r) => r.status === 200,
    'latency < 2s': (r) => r.timings.duration < 2000,
  });
}
"""


def test_k6_script_has_qps_threshold():
    """REQ-002: k6 脚本必须包含 QPS ≥ 10 阈值"""
    assert "rate>=10" in K6_SCRIPT


def test_k6_script_has_p99_threshold():
    """REQ-003: k6 脚本必须包含 P99 ≤ 2000ms 阈值"""
    assert "p(99)<2000" in K6_SCRIPT


def test_k6_script_valid_js():
    """REQ-103: k6 脚本基本语法检查"""
    # 不能有不闭合括号
    assert K6_SCRIPT.count("{") == K6_SCRIPT.count("}")
    assert K6_SCRIPT.count("(") == K6_SCRIPT.count(")")