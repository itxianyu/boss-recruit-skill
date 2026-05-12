from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None

try:
    from openpyxl import Workbook
except ImportError:  # pragma: no cover
    Workbook = None

try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:  # pragma: no cover
    SentenceTransformer = None
    util = None


DEFAULT_RESUMES: List[Dict[str, Any]] = [
    {
        "name": "张三",
        "skills": ["Python", "Django", "REST API", "MySQL"],
        "experience": 4,
        "age": 28,
        "city": "上海",
        "work_address": "上海浦东",
        "education": "本科",
        "salary_k": 28,
        "projects": ["电商订单系统", "供应链管理平台"],
        "job_requirements": ["Python", "Django", "MySQL", "REST API"],
        "summary": "偏后端服务开发，熟悉接口设计和性能优化。",
    },
    {
        "name": "李四",
        "skills": ["Python", "Flask", "Redis", "Docker"],
        "experience": 3,
        "age": 26,
        "city": "上海",
        "work_address": "上海徐汇",
        "education": "本科",
        "salary_k": 24,
        "projects": ["营销活动平台", "数据采集服务"],
        "job_requirements": ["Python", "Flask", "Redis", "Docker"],
        "summary": "偏业务系统交付，能独立负责中小型服务。",
    },
    {
        "name": "王五",
        "skills": ["Java", "Spring Boot", "MySQL", "Kafka"],
        "experience": 5,
        "age": 32,
        "city": "杭州",
        "work_address": "杭州滨江",
        "education": "本科",
        "salary_k": 35,
        "projects": ["支付清结算系统"],
        "job_requirements": ["Java", "Spring Boot", "Kafka"],
        "summary": "主栈 Java，转 Python 成本较高。",
    },
]


CITY_VALUES = ["上海", "北京", "深圳", "广州", "杭州", "苏州", "成都", "武汉", "南京"]
EDUCATION_VALUES = ["大专", "本科", "硕士", "博士"]
KNOWN_SKILLS = [
    "Python",
    "Django",
    "Flask",
    "FastAPI",
    "REST API",
    "Redis",
    "MySQL",
    "PostgreSQL",
    "Docker",
    "Kubernetes",
    "Java",
    "Spring Boot",
    "Kafka",
]
KNOWN_TITLES = [
    "Python 后端开发",
    "Python开发",
    "后端开发",
    "Java 后端开发",
    "算法工程师",
    "数据分析师",
    "产品经理",
]


@dataclass
class JobRequest:
    title: str
    skills: List[str] = field(default_factory=list)
    experience: int = 0
    city: str = ""
    education: str = ""
    work_address: str = ""
    max_age: int = 0
    salary_min_k: int = 0
    salary_max_k: int = 0
    job_requirements: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobRequest":
        return cls(
            title=str(data.get("title", "")).strip(),
            skills=[str(item).strip() for item in data.get("skills", []) if str(item).strip()],
            experience=_safe_int(data.get("experience", 0)),
            city=str(data.get("city", "")).strip(),
            education=str(data.get("education", "")).strip(),
            work_address=str(data.get("work_address", "")).strip(),
            max_age=_safe_int(data.get("max_age", 0)),
            salary_min_k=_safe_int(data.get("salary_min_k", 0)),
            salary_max_k=_safe_int(data.get("salary_max_k", 0)),
            job_requirements=[str(item).strip() for item in data.get("job_requirements", []) if str(item).strip()],
        )


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class BossRecruitSkill:
    def __init__(
        self,
        output_dir: str = "artifacts",
        resume_data_path: Optional[str] = None,
        embedding_model_name: str = "all-MiniLM-L6-v2",
        codex_config_path: Optional[str] = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.resume_data_path = Path(resume_data_path) if resume_data_path else None
        self.embedding_model_name = embedding_model_name
        self._embedding_model = None
        self.codex_config_path = Path(codex_config_path) if codex_config_path else Path.home() / ".codex" / "config.toml"

    def prepare_execution(self, symptom_text: str = "") -> Dict[str, Any]:
        health = self.health_check(symptom_text=symptom_text)
        return self._build_diagnostic_result(
            status=health["status"],
            ready=health["status"] == "ready",
            next_actions=health["next_actions"],
            health_check=health,
        )

    def search_and_generate(self, job_req: Dict[str, Any]) -> Dict[str, Any]:
        readiness = self.prepare_execution()
        if readiness["status"] != "ready":
            return self._build_blocked_result(reason=readiness["status"], health_check=readiness)

        parsed_request = JobRequest.from_dict(job_req)
        self._validate_job_request(parsed_request)

        resumes = self._fetch_resumes(parsed_request)
        matched = self._match_resumes(parsed_request, resumes)
        pdf_files = [self._generate_pdf(parsed_request, resume) for resume in matched]
        excel_file = self._generate_excel(matched)

        return self._build_success_result(
            job_request=asdict(parsed_request),
            resumes=matched,
            pdf_files=[str(path) for path in pdf_files],
            excel_file=str(excel_file),
            data_source=self._data_source_label(),
        )

    def search_and_generate_from_text(self, request_text: str) -> Dict[str, Any]:
        readiness = self.prepare_execution(symptom_text=request_text)
        if readiness["status"] != "ready":
            return self._build_blocked_result(
                reason=readiness["status"],
                health_check=readiness,
                request_text=request_text,
            )

        job_req = self.parse_job_request(request_text)
        result = self.search_and_generate(job_req)
        result["request_text"] = request_text
        return result

    def parse_job_request(self, request_text: str) -> Dict[str, Any]:
        text = request_text.strip()
        city = self._extract_first(text, CITY_VALUES)
        education = self._extract_first(text, EDUCATION_VALUES)
        experience = self._extract_number(text, [r"(\d+)\s*年经验", r"(\d+)\s*年"])
        max_age = self._extract_number(text, [r"年龄.*?(\d+)\s*岁", r"(\d+)\s*岁以下", r"(\d+)\s*岁"])
        salary_range = self._extract_salary_range(text)
        title = self._guess_title(text)
        skills = self._extract_skills(text)
        work_address = self._extract_work_address(text)
        job_requirements = self._extract_job_requirements(text)

        return {
            "title": title or "未指定岗位",
            "skills": skills,
            "experience": experience,
            "city": city or "",
            "education": education or "",
            "work_address": work_address,
            "max_age": max_age,
            "salary_min_k": salary_range[0],
            "salary_max_k": salary_range[1],
            "job_requirements": job_requirements,
        }

    def detect_boss_mcp_registration(self) -> Dict[str, Any]:
        config_exists = self.codex_config_path.exists()
        has_registration = False

        if config_exists:
            content = self.codex_config_path.read_text(encoding="utf-8", errors="ignore")
            has_registration = "[mcp_servers.boss-zhipin]" in content

        return {
            "config_path": str(self.codex_config_path),
            "config_exists": config_exists,
            "boss_zhipin_registered": has_registration,
            "setup_script": str(Path(__file__).resolve().parent / "scripts" / "register_boss_mcp.ps1"),
        }

    def health_check(self, symptom_text: str = "") -> Dict[str, Any]:
        python_available = shutil.which("python") is not None or shutil.which("py") is not None
        registration = self.detect_boss_mcp_registration()
        issue_diagnosis = self.diagnose_boss_mcp_issue(symptom_text) if symptom_text else None

        status = "ready"
        next_actions: List[str] = []

        if not python_available:
            status = "python_missing"
            next_actions.append("install Python and requirements by using scripts/bootstrap_python_env.ps1")

        if not registration["boss_zhipin_registered"]:
            if status == "ready":
                status = "mcp_missing"
            next_actions.append("register boss-zhipin MCP by using scripts/register_boss_mcp.ps1")

        if issue_diagnosis and issue_diagnosis.get("issue_type") == "boss_mcp_loop_or_redirect":
            status = "mcp_unstable"
            next_actions.extend(issue_diagnosis["recommended_actions"])

        if not next_actions:
            next_actions.append("proceed with the recruiting workflow")

        return {
            "status": status,
            "python_available": python_available,
            "boss_mcp_registered": registration["boss_zhipin_registered"],
            "config_path": registration["config_path"],
            "setup_script": registration["setup_script"],
            "disable_script": str(Path(__file__).resolve().parent / "scripts" / "disable_boss_mcp.ps1"),
            "next_actions": next_actions,
            "issue_diagnosis": issue_diagnosis,
        }

    def build_boss_mcp_config(self, cookie: str, bst: str) -> str:
        return (
            "[mcp_servers.boss-zhipin]\n"
            'command = "npx"\n'
            'args = ["-y", "mcp-boss-zp"]\n\n'
            "[mcp_servers.boss-zhipin.env]\n"
            f'BST = "{bst}"\n'
            f'COOKIE = "{cookie}"\n'
        )

    def diagnose_boss_mcp_issue(self, symptom_text: str) -> Dict[str, Any]:
        text = symptom_text.lower()
        repeated_open = any(token in text for token in ["不停打开", "重复打开", "反复打开", "keep opening", "opens repeatedly"])
        maintenance = any(token in text for token in ["停止维护", "自动跳转", "maintenance", "redirect"])

        if repeated_open or maintenance:
            return {
                "issue_type": "boss_mcp_loop_or_redirect",
                "likely_cause": "third_party_mcp_browser_flow_failed_or_deprecated_route",
                "recommended_actions": [
                    "stop retrying the MCP",
                    "disable boss-zhipin MCP temporarily",
                    "refresh COOKIE and BST",
                    "re-register the MCP",
                    "restart Codex before testing again",
                    "use offline mode until MCP is stable",
                ],
                "disable_script": str(Path(__file__).resolve().parent / "scripts" / "disable_boss_mcp.ps1"),
            }

        return {
            "issue_type": "unknown",
            "recommended_actions": [
                "check MCP registration",
                "check COOKIE and BST",
                "review current MCP logs or terminal output",
            ],
        }

    def _build_blocked_result(
        self,
        reason: str,
        health_check: Dict[str, Any],
        request_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        result = {
            "schema_version": "1.0",
            "result_type": "blocked",
            "status": reason,
            "blocked": True,
            "reason": reason,
            "next_actions": health_check.get("next_actions", []),
            "health_check": health_check,
        }
        if request_text is not None:
            result["request_text"] = request_text
        return result

    def _build_success_result(
        self,
        job_request: Dict[str, Any],
        resumes: List[Dict[str, Any]],
        pdf_files: List[str],
        excel_file: str,
        data_source: str,
    ) -> Dict[str, Any]:
        return {
            "schema_version": "1.0",
            "result_type": "success",
            "status": "ready",
            "blocked": False,
            "job_request": job_request,
            "resumes": resumes,
            "pdf_files": pdf_files,
            "excel_file": excel_file,
            "data_source": data_source,
        }

    def _build_diagnostic_result(
        self,
        status: str,
        ready: bool,
        next_actions: List[str],
        health_check: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "schema_version": "1.0",
            "result_type": "diagnostic",
            "status": status,
            "ready": ready,
            "blocked": not ready,
            "next_actions": next_actions,
            "health_check": health_check,
        }

    def _validate_job_request(self, job_req: JobRequest) -> None:
        if not job_req.title:
            raise ValueError("job_req.title is required")

    def _fetch_resumes(self, job_req: JobRequest) -> List[Dict[str, Any]]:
        if self.resume_data_path and self.resume_data_path.exists():
            with self.resume_data_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, list):
                raise ValueError("resume_data_path must contain a JSON array")
            return [self._normalize_resume(item) for item in data]

        return [self._normalize_resume(item) for item in DEFAULT_RESUMES]

    def _normalize_resume(self, item: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(item)
        normalized["skills"] = [str(skill).strip() for skill in item.get("skills", []) if str(skill).strip()]
        normalized["projects"] = [str(project).strip() for project in item.get("projects", []) if str(project).strip()]
        normalized["job_requirements"] = [
            str(req).strip() for req in item.get("job_requirements", normalized["skills"]) if str(req).strip()
        ]
        normalized["experience"] = _safe_int(item.get("experience", 0))
        normalized["age"] = _safe_int(item.get("age", 0))
        normalized["salary_k"] = _safe_int(item.get("salary_k", 0))
        normalized["city"] = str(item.get("city", "")).strip()
        normalized["work_address"] = str(item.get("work_address", normalized["city"])).strip()
        normalized["education"] = str(item.get("education", "")).strip()
        normalized["name"] = str(item.get("name", "")).strip()
        normalized["summary"] = str(item.get("summary", "")).strip()
        return normalized

    def _match_resumes(self, job_req: JobRequest, resumes: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        scored_resumes = []
        for resume in resumes:
            if not self._passes_filters(job_req, resume):
                continue
            score_details = self._score_resume(job_req, resume)
            enriched = dict(resume)
            enriched.update(score_details)
            scored_resumes.append(enriched)

        return sorted(scored_resumes, key=lambda item: item["match_score"], reverse=True)

    def _score_resume(self, job_req: JobRequest, resume: Dict[str, Any]) -> Dict[str, Any]:
        skill_overlap = self._skill_overlap_score(job_req.skills, resume.get("skills", []))
        experience_score = self._experience_score(job_req.experience, resume.get("experience", 0))
        city_score = 1.0 if not job_req.city or job_req.city == resume.get("city", "") else 0.0
        work_address_score = 1.0 if not job_req.work_address or job_req.work_address in resume.get("work_address", "") else 0.0
        education_score = self._education_score(job_req.education, resume.get("education", ""))
        age_score = self._age_score(job_req.max_age, resume.get("age", 0))
        salary_score = self._salary_score(job_req.salary_min_k, job_req.salary_max_k, resume.get("salary_k", 0))
        requirement_score = self._requirement_score(job_req.job_requirements, resume.get("job_requirements", []))
        semantic_score = self._semantic_score(job_req, resume)

        weighted = (
            skill_overlap * 0.30
            + experience_score * 0.15
            + city_score * 0.10
            + work_address_score * 0.10
            + education_score * 0.05
            + age_score * 0.05
            + salary_score * 0.10
            + requirement_score * 0.10
            + semantic_score * 0.05
        )

        reasons = []
        if skill_overlap > 0:
            reasons.append(f"技能匹配 {skill_overlap:.2f}")
        if experience_score > 0:
            reasons.append(f"经验匹配 {experience_score:.2f}")
        if city_score == 1.0 and job_req.city:
            reasons.append("城市匹配")
        if work_address_score == 1.0 and job_req.work_address:
            reasons.append("上班地址匹配")
        if education_score > 0 and job_req.education:
            reasons.append("学历满足")
        if age_score > 0 and job_req.max_age:
            reasons.append("年龄满足")
        if salary_score > 0 and (job_req.salary_min_k or job_req.salary_max_k):
            reasons.append("薪资区间匹配")
        if requirement_score > 0 and job_req.job_requirements:
            reasons.append(f"岗位要求匹配 {requirement_score:.2f}")
        if semantic_score > 0:
            reasons.append(f"语义相似 {semantic_score:.2f}")

        return {
            "match_score": round(weighted, 3),
            "match_reasons": reasons,
        }

    def _skill_overlap_score(self, required_skills: List[str], resume_skills: List[str]) -> float:
        if not required_skills:
            return 0.5
        required = {skill.lower() for skill in required_skills}
        actual = {skill.lower() for skill in resume_skills}
        return len(required & actual) / len(required)

    def _experience_score(self, required_years: int, actual_years: int) -> float:
        if required_years <= 0:
            return 0.5
        if actual_years >= required_years:
            return 1.0
        return max(0.0, actual_years / required_years)

    def _age_score(self, max_age: int, actual_age: int) -> float:
        if max_age <= 0 or actual_age <= 0:
            return 0.5
        return 1.0 if actual_age <= max_age else 0.0

    def _salary_score(self, salary_min_k: int, salary_max_k: int, actual_salary_k: int) -> float:
        if salary_min_k <= 0 and salary_max_k <= 0:
            return 0.5
        if actual_salary_k <= 0:
            return 0.0
        if salary_min_k and actual_salary_k < salary_min_k:
            return 0.0
        if salary_max_k and actual_salary_k > salary_max_k:
            return 0.0
        return 1.0

    def _requirement_score(self, required_items: List[str], actual_items: List[str]) -> float:
        if not required_items:
            return 0.5
        required = {item.lower() for item in required_items}
        actual = {item.lower() for item in actual_items}
        return len(required & actual) / len(required)

    def _education_score(self, required: str, actual: str) -> float:
        if not required:
            return 0.5
        rank = {"大专": 1, "本科": 2, "硕士": 3, "博士": 4}
        return 1.0 if rank.get(actual, 0) >= rank.get(required, 0) else 0.0

    def _passes_filters(self, job_req: JobRequest, resume: Dict[str, Any]) -> bool:
        if job_req.city and job_req.city != resume.get("city", ""):
            return False
        if job_req.work_address and job_req.work_address not in resume.get("work_address", ""):
            return False
        if job_req.max_age and resume.get("age", 0) and resume.get("age", 0) > job_req.max_age:
            return False
        if job_req.experience and resume.get("experience", 0) < job_req.experience:
            return False
        if job_req.salary_min_k and resume.get("salary_k", 0) and resume.get("salary_k", 0) < job_req.salary_min_k:
            return False
        if job_req.salary_max_k and resume.get("salary_k", 0) and resume.get("salary_k", 0) > job_req.salary_max_k:
            return False
        return True

    def _semantic_score(self, job_req: JobRequest, resume: Dict[str, Any]) -> float:
        if SentenceTransformer is None or util is None:
            return 0.0

        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer(self.embedding_model_name)

        job_text = self._job_text(job_req)
        resume_text = self._resume_text(resume)
        job_vector = self._embedding_model.encode(job_text)
        resume_vector = self._embedding_model.encode(resume_text)
        return max(0.0, float(util.cos_sim(job_vector, resume_vector).item()))

    def _job_text(self, job_req: JobRequest) -> str:
        return (
            f"岗位:{job_req.title} "
            f"技能:{','.join(job_req.skills)} "
            f"经验:{job_req.experience}年 "
            f"城市:{job_req.city} "
            f"上班地址:{job_req.work_address} "
            f"学历:{job_req.education} "
            f"年龄:{job_req.max_age} "
            f"薪资:{job_req.salary_min_k}-{job_req.salary_max_k}k "
            f"要求:{','.join(job_req.job_requirements)}"
        )

    def _resume_text(self, resume: Dict[str, Any]) -> str:
        return (
            f"技能:{','.join(resume.get('skills', []))} "
            f"经验:{resume.get('experience', 0)}年 "
            f"城市:{resume.get('city', '')} "
            f"上班地址:{resume.get('work_address', '')} "
            f"学历:{resume.get('education', '')} "
            f"年龄:{resume.get('age', 0)} "
            f"薪资:{resume.get('salary_k', 0)}k "
            f"项目:{','.join(resume.get('projects', []))} "
            f"要求:{','.join(resume.get('job_requirements', []))} "
            f"总结:{resume.get('summary', '')}"
        )

    def _generate_pdf(self, job_req: JobRequest, resume: Dict[str, Any]) -> Path:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

        file_path = self.output_dir / f"{resume['name']}.pdf"
        pdf = canvas.Canvas(str(file_path), pagesize=A4)
        pdf.setTitle(f"{resume['name']}_match_summary")
        pdf.setFont("STSong-Light", 14)

        lines = [
            f"岗位: {job_req.title}",
            f"候选人: {resume['name']}",
            f"匹配分: {resume['match_score']}",
            f"技能: {', '.join(resume.get('skills', []))}",
            f"经验: {resume.get('experience', 0)} 年",
            f"年龄: {resume.get('age', 0)} 岁",
            f"城市: {resume.get('city', '')}",
            f"上班地址: {resume.get('work_address', '')}",
            f"学历: {resume.get('education', '')}",
            f"期望薪资: {resume.get('salary_k', 0)}k",
            f"岗位要求: {', '.join(resume.get('job_requirements', []))}",
            f"项目: {', '.join(resume.get('projects', []))}",
            f"说明: {'; '.join(resume.get('match_reasons', []))}",
            f"摘要: {resume.get('summary', '')}",
        ]

        y = 800
        for line in lines:
            pdf.drawString(48, y, line)
            y -= 24
            if y < 72:
                pdf.showPage()
                pdf.setFont("STSong-Light", 14)
                y = 800

        pdf.save()
        return file_path

    def _generate_excel(self, matched: List[Dict[str, Any]]) -> Path:
        file_path = self.output_dir / f"matched_candidates_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
        rows = []
        for item in matched:
            rows.append(
                {
                    "name": item.get("name", ""),
                    "match_score": item.get("match_score", 0),
                    "skills": ", ".join(item.get("skills", [])),
                    "experience": item.get("experience", 0),
                    "age": item.get("age", 0),
                    "city": item.get("city", ""),
                    "work_address": item.get("work_address", ""),
                    "education": item.get("education", ""),
                    "salary_k": item.get("salary_k", 0),
                    "projects": ", ".join(item.get("projects", [])),
                    "job_requirements": ", ".join(item.get("job_requirements", [])),
                    "match_reasons": "; ".join(item.get("match_reasons", [])),
                }
            )

        if pd is not None:
            pd.DataFrame(rows).to_excel(file_path, index=False)
            return file_path

        if Workbook is not None:
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.title = "matched_candidates"
            headers = list(rows[0].keys()) if rows else [
                "name",
                "match_score",
                "skills",
                "experience",
                "age",
                "city",
                "work_address",
                "education",
                "salary_k",
                "projects",
                "job_requirements",
                "match_reasons",
            ]
            worksheet.append(headers)
            for row in rows:
                worksheet.append([row.get(header, "") for header in headers])
            workbook.save(file_path)
            return file_path

        raise RuntimeError("Excel generation requires pandas or openpyxl. Install dependencies from requirements.txt.")

    def _extract_first(self, text: str, values: List[str]) -> str:
        for value in values:
            if value in text:
                return value
        return ""

    def _extract_number(self, text: str, patterns: List[str]) -> int:
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
        return 0

    def _extract_salary_range(self, text: str) -> tuple[int, int]:
        patterns = [
            r"(\d+)\s*[-~]\s*(\d+)\s*[kK]",
            r"(\d+)\s*到\s*(\d+)\s*[kK]",
            r"(\d+)\s*-\s*(\d+)\s*千",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1)), int(match.group(2))
        return 0, 0

    def _extract_skills(self, text: str) -> List[str]:
        return [skill for skill in KNOWN_SKILLS if skill.lower() in text.lower()]

    def _extract_work_address(self, text: str) -> str:
        patterns = [
            r"上班地址[:：]?\s*([^\s，。,；;]+)",
            r"工作地址[:：]?\s*([^\s，。,；;]+)",
            r"在([^\s，。,；;]+)上班",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_job_requirements(self, text: str) -> List[str]:
        requirements = []
        patterns = [
            r"岗位要求[:：]?\s*([^\n]+)",
            r"技能要求[:：]?\s*([^\n]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                raw = re.split(r"[，,；;、]", match.group(1))
                requirements.extend([item.strip() for item in raw if item.strip()])
        for skill in self._extract_skills(text):
            if skill not in requirements:
                requirements.append(skill)
        return requirements

    def _guess_title(self, text: str) -> str:
        for title in KNOWN_TITLES:
            if title.lower() in text.lower():
                return title
        match = re.search(r"找(.+?)(并生成|生成|，|,|。|$)", text)
        if match:
            return match.group(1).strip()
        return ""

    def _data_source_label(self) -> str:
        if self.resume_data_path and self.resume_data_path.exists():
            return f"local_json:{self.resume_data_path}"
        return "built_in_sample_data"


if __name__ == "__main__":
    skill = BossRecruitSkill()
    demo = skill.search_and_generate_from_text(
        "帮我找上海 Python 后端开发，要求 3 年经验，30 岁以下，本科，25-30k，上班地址上海浦东，岗位要求 Python、Django、MySQL，生成 PDF 和 Excel"
    )
    print(json.dumps(demo, ensure_ascii=False, indent=2))
