"""实验和想法管理服务 - 代理到 storage 层"""
from typing import List, Dict, Optional
import services.storage as _s


# ── 实验想法 ──────────────────────────────────────

def get_experiment_ideas(status: Optional[str] = None) -> List[Dict]:
    return _s.get_ideas(status)


def get_experiment_idea_by_id(idea_id: str) -> Optional[Dict]:
    return _s.get_idea_by_id(idea_id)


def create_experiment_idea(data: Dict) -> Dict:
    return _s.create_idea(data)


def update_idea_status(idea_id: str, status: str) -> Optional[Dict]:
    return _s.update_idea_status_by_id(idea_id, status)


def delete_idea(idea_id: str) -> bool:
    return _s.delete_idea_by_id(idea_id)


def get_ideas_stats() -> Dict:
    return _s.get_ideas_stats()


# ── 实验 ──────────────────────────────────────────

def get_experiments(status: Optional[str] = None) -> List[Dict]:
    return _s.get_experiments(status)


def get_experiment_by_id(exp_id: str) -> Optional[Dict]:
    return _s.get_experiment_by_id(exp_id)


def create_experiment(data: Dict) -> Dict:
    return _s.create_experiment(data)


def update_experiment(exp_id: str, data: Dict) -> Optional[Dict]:
    return _s.update_experiment_by_id(exp_id, data)


def delete_experiment(exp_id: str) -> bool:
    return _s.delete_experiment_by_id(exp_id)


# ── 实验日志 ──────────────────────────────────────

def get_experiment_logs(exp_id: str) -> List[Dict]:
    return _s.get_logs_for_experiment(exp_id)


def add_experiment_log(exp_id: str, content: str) -> Dict:
    return _s.add_log(exp_id, content)
