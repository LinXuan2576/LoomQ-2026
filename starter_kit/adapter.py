#!/usr/bin/env python3
"""LoomQ submission adapter contract v1.0.

L1 实现状态（增量开发中）：
- spinq  : ✅ transpile + run（本地模拟器）
- originq: 🔜 youneiga 负责（QASM → OriginIR + pyqpanda CPUQVM）
- braket : 🔜 D2（QASM2.0 → OpenQASM3 改写 + LocalSimulator）

核心原则：三后端共用同一套统一结果 Schema；meta 禁止 is_mock。
"""

import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


SUPPORTED_TARGETS = ("spinq", "originq", "braket")


def transpile(qasm_str: str, target: str) -> str:
    """Translate OpenQASM 2.0 into the target backend's native representation."""
    if target not in SUPPORTED_TARGETS:
        raise ValueError("unsupported target: %r" % (target,))
    if target == "spinq":
        # 量旋 SDK 自带 QASM 编译器（get_compiler("qasm")），原生接受 QASM 2.0，
        # 无需任何改写 —— 直接原样返回。
        return qasm_str
    raise NotImplementedError("target not implemented yet: %r" % (target,))


def run(qasm_str: str, target: str, shots: int) -> Dict[str, Any]:
    """Execute a circuit and return the unified result schema from the rules."""
    if target not in SUPPORTED_TARGETS:
        raise ValueError("unsupported target: %r" % (target,))
    if target == "spinq":
        return _run_spinq(qasm_str, shots)
    raise NotImplementedError("target not implemented yet: %r" % (target,))


def _run_spinq(qasm_str: str, shots: int) -> Dict[str, Any]:
    """量旋本地模拟器执行：QASM → IR → BasicSimulator → 统一 Schema。"""
    import spinqit as sq
    from spinqit import BasicSimulatorConfig, get_basic_simulator, get_compiler

    # QASMCompiler 接受文件路径，所以先写临时文件
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".qasm", delete=False, encoding="utf-8"
    )
    try:
        tmp.write(qasm_str)
        tmp.close()
        compiler = get_compiler("qasm")
        ir = compiler.compile(tmp.name, 0)
    finally:
        os.unlink(tmp.name)

    engine = get_basic_simulator()
    config = BasicSimulatorConfig()
    config.configure_shots(shots)
    result = engine.execute(ir, config)
    counts = result.counts

    return {
        "backend": "spinq_basic_simulator",
        "job_id": (
            getattr(result, "job_id", None)
            or getattr(result, "task_id", None)
            or "spinq-local-%04x" % (abs(hash(qasm_str)) & 0xFFFF)
        ),
        "shots": shots,
        "counts": {str(key): value for key, value in counts.items()},
        "bit_order": "little",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "meta": {"qubits_count": ir.qnum},
    }


def agent_chat(prompt: str) -> str:
    """Optional L2 entry point using the documented LOOMQ_LLM_* environment."""
    raise NotImplementedError("L2 is optional; implement agent_chat(prompt) to enter")


def compile_hybrid(hybrid_qasm_str: str) -> Tuple[List[str], str]:
    """Optional L3 entry point. Return quantum operations and RISC-V assembly."""
    raise NotImplementedError(
        "L3 is optional; implement compile_hybrid(hybrid_qasm_str) to enter"
    )
