import os
import json
import re
from html import unescape

import bleach
import markdown as md
import structlog
import yaml
from flask import Flask, render_template, request, jsonify, url_for, Response, stream_with_context
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from markupsafe import Markup
from prometheus_flask_exporter import PrometheusMetrics
import config
import ai_providers
import instructor_agent

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

logger = structlog.get_logger(__name__)
limiter = Limiter(get_remote_address, app=app, default_limits=[])
metrics = PrometheusMetrics(app)

MARKDOWN_EXTENSIONS = [
    "fenced_code",
    "pymdownx.superfences",
    "tables",
    "nl2br",
    "codehilite",
    "attr_list",
]

BLEACH_ALLOWED_TAGS = list(bleach.sanitizer.ALLOWED_TAGS) + [
    "p",
    "pre",
    "code",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "img",
    "div",
    "span",
    "br",
]
BLEACH_ALLOWED_ATTRS = {
    "*": ["class"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "class"],
}

MERMAID_BLOCK_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)


@app.context_processor
def inject_static_asset_url():
    """Provide a cache-busted static asset URL helper for templates."""
    def static_asset_url(filename):
        static_path = os.path.join(app.static_folder, filename)
        if os.path.isfile(static_path):
            version = int(os.path.getmtime(static_path))
            return url_for("static", filename=filename, v=version)
        return url_for("static", filename=filename)

    return {"static_asset_url": static_asset_url}

CATEGORIES = {
    "networking": {
        "title": "Networking",
        "icon": "🌐",
        "description": "Learn fundamental and advanced networking concepts including OSI model, TCP/IP, subnetting, and more.",
        "color": "blue",
        "sequence": 3,
        "year": 2,
        "prev_course": "linux",
        "next_course": "cisco",
        "builds_on": [
            "Linux command-line (SYS 202) — you will use ssh, ping, traceroute, ip addr, ss, and tcpdump throughout every lab",
            "Binary arithmetic (MATH 110) — subnetting calculations depend on binary-to-decimal conversion",
        ],
        "leads_to": "Cisco Enterprise Networking (NET 310), where you apply IP addressing and routing theory to real Cisco IOS devices",
        "course_number": "NET 201",
        "credits": 3,
        "lab_credits": 1,
        "department": "Department of Computer Science & Network Engineering",
        "prerequisites": ["Introduction to Linux (SYS 202)", "College Mathematics (MATH 110)"],
        "catalog_description": (
            "A rigorous introduction to data communications and computer networking. "
            "Topics include the OSI and TCP/IP reference models, IPv4/IPv6 addressing and "
            "subnetting, transport-layer protocols (TCP and UDP), DNS, and network "
            "troubleshooting methodologies. Laboratory sessions provide hands-on packet "
            "analysis using Wireshark and topology simulation in Cisco Packet Tracer. "
            "Prepares students for the CompTIA Network+ and Cisco CCNA examinations."
        ),
        "textbooks": [
            {
                "title": "Computer Networks",
                "authors": "Andrew S. Tanenbaum & David J. Wetherall",
                "edition": "6th ed., Pearson, 2021",
                "isbn": "978-0-13-468286-5",
            },
            {
                "title": "CompTIA Network+ Study Guide",
                "authors": "Todd Lammle",
                "edition": "4th ed., Sybex, 2022",
                "isbn": "978-1-119-81239-4",
            },
        ],
        "faculty": {
            "role": "Course Coordinator",
            "note": "Instruction delivered by faculty of the Department of Computer Science & Network Engineering.",
        },
    },
    "cisco": {
        "title": "Cisco",
        "icon": "🔧",
        "description": "Master Cisco IOS, VLANs, routing protocols, switching, and enterprise networking.",
        "color": "teal",
        "sequence": 6,
        "year": 3,
        "prev_course": "networking",
        "next_course": "cybersecurity",
        "builds_on": [
            "IP addressing and subnetting (NET 201) — every lab requires you to design and assign subnets",
            "OSI model layers (NET 201) — IOS show commands map directly to Layer 2 (MAC/VLAN) and Layer 3 (IP/routing) concepts",
            "Linux SSH and SCP (SYS 202) — you SSH into routers and use SCP to back up configurations",
        ],
        "leads_to": "Edge AI Development (AI 340), where solid network infrastructure skills underpin multi-device AI deployments",
        "course_number": "NET 310",
        "credits": 3,
        "lab_credits": 2,
        "department": "Department of Computer Science & Network Engineering",
        "prerequisites": ["Networking Fundamentals (NET 201)", "Introduction to Linux (SYS 202)"],
        "catalog_description": (
            "An advanced course in enterprise networking using Cisco IOS. "
            "Students configure and troubleshoot routers, switches, VLANs, inter-VLAN routing, "
            "Spanning Tree Protocol (STP), static and dynamic routing (OSPF, EIGRP), "
            "access control lists (ACLs), and Network Address Translation (NAT). "
            "Extensive laboratory work in a simulated Cisco environment. "
            "This course prepares students for the Cisco Certified Network Associate (CCNA 200-301) examination."
        ),
        "textbooks": [
            {
                "title": "CCNA 200-301 Official Cert Guide, Volume 1",
                "authors": "Wendell Odom",
                "edition": "Cisco Press, 2020",
                "isbn": "978-0-13-523792-5",
            },
            {
                "title": "CCNA 200-301 Official Cert Guide, Volume 2",
                "authors": "Wendell Odom",
                "edition": "Cisco Press, 2020",
                "isbn": "978-0-13-523796-3",
            },
        ],
        "faculty": {
            "role": "Course Coordinator",
            "note": "Instruction delivered by Cisco Certified faculty (CCNP/CCIE) of the Department of Computer Science & Network Engineering.",
        },
    },
    "python": {
        "title": "Python",
        "icon": "🐍",
        "description": "Learn Python programming from basics to advanced topics including network automation.",
        "color": "green",
        "sequence": 2,
        "year": 1,
        "prev_course": "linux",
        "next_course": "networking",
        "builds_on": [
            "Linux shell and file system (SYS 202) — Python scripts run from Bash and interact with the Linux filesystem daily",
            "File permissions and processes (SYS 202) — Python automation manages files, processes, and services",
            "Networking fundamentals (NET 201) — the network-automation modules assume fluency with IP addressing and SSH",
        ],
        "leads_to": "Edge AI Development (AI 340), which requires Python for model training, inference pipelines, and hardware control",
        "course_number": "CS 215",
        "credits": 3,
        "lab_credits": 1,
        "department": "Department of Computer Science & Software Engineering",
        "prerequisites": ["Introduction to Linux (SYS 202)", "Networking Fundamentals (NET 201)"],
        "catalog_description": (
            "An intermediate course in Python programming with emphasis on practical "
            "applications in systems administration and network automation. "
            "Topics include data structures, file I/O, regular expressions, object-oriented "
            "programming, exception handling, and the use of third-party libraries including "
            "Netmiko, Paramiko, NAPALM, and Nornir for network device automation. "
            "Students complete a capstone project automating a multi-device network configuration task."
        ),
        "textbooks": [
            {
                "title": "Python Crash Course",
                "authors": "Eric Matthes",
                "edition": "3rd ed., No Starch Press, 2023",
                "isbn": "978-1-7185-0270-4",
            },
            {
                "title": "Network Programmability and Automation",
                "authors": "Jason Edelman, Scott S. Lowe & Matt Oswalt",
                "edition": "2nd ed., O'Reilly, 2023",
                "isbn": "978-1-098-11083-3",
            },
        ],
        "faculty": {
            "role": "Course Coordinator",
            "note": "Instruction delivered by faculty of the Department of Computer Science & Software Engineering.",
        },
    },
    "linux": {
        "title": "Linux",
        "icon": "🐧",
        "description": "Master Linux commands, file system management, shell scripting, and system administration.",
        "color": "orange",
        "sequence": 1,
        "year": 1,
        "prev_course": None,
        "next_course": "python",
        "builds_on": [
            "Basic computer literacy — familiarity with files, folders, and operating systems at the end-user level",
        ],
        "leads_to": "Networking (NET 201) and Python Programming (CS 215), both of which assume daily Bash shell proficiency",
        "course_number": "SYS 202",
        "credits": 3,
        "lab_credits": 1,
        "department": "Department of Systems Administration & Cybersecurity",
        "prerequisites": ["Introduction to Computing (CS 101)"],
        "catalog_description": (
            "A comprehensive introduction to Linux system administration. "
            "Students develop proficiency with the Bash shell, the Filesystem Hierarchy Standard (FHS), "
            "file permissions and ownership, process management, package management, networking tools, "
            "and shell scripting. Laboratory sessions are conducted on live Ubuntu/Debian virtual machines. "
            "Successful students earn the Linux Foundation Certified System Administrator (LFCS) skill set "
            "and are prepared for the CompTIA Linux+ examination."
        ),
        "textbooks": [
            {
                "title": "The Linux Command Line",
                "authors": "William E. Shotts Jr.",
                "edition": "2nd ed., No Starch Press, 2019",
                "isbn": "978-1-59327-952-9",
            },
            {
                "title": "UNIX and Linux System Administration Handbook",
                "authors": "Evi Nemeth, Garth Snyder, Trent R. Hein & Ben Whaley",
                "edition": "5th ed., Pearson, 2017",
                "isbn": "978-0-13-468733-4",
            },
        ],
        "faculty": {
            "role": "Course Coordinator",
            "note": "Instruction delivered by Linux Foundation Certified faculty of the Department of Systems Administration & Cybersecurity.",
        },
    },
    "jetson": {
        "title": "Jetson AI",
        "icon": "🤖",
        "description": "Build practical edge AI workflows on NVIDIA Jetson Orin Nano 8GB: setup, media generation, and computer vision.",
        "color": "purple",
        "sequence": 9,
        "year": 4,
        "prev_course": "cloud",
        "next_course": None,
        "builds_on": [
            "Python programming (CS 215) — all inference pipelines, training scripts, and automation are written in Python",
            "Linux system administration (SYS 202) — Jetson runs Ubuntu/L4T; you configure services, manage storage, and write systemd units",
            "Networking fundamentals (NET 201) — edge devices communicate over networks; IP addressing and SSH are assumed knowledge",
        ],
        "leads_to": "Graduate-level AI systems research or industry roles in robotics, autonomous vehicles, and edge computing",
        "course_number": "AI 340",
        "credits": 3,
        "lab_credits": 2,
        "department": "Department of Artificial Intelligence & Robotics",
        "prerequisites": ["Python Programming (CS 215)", "Introduction to Linux (SYS 202)", "Introduction to Machine Learning (AI 201)"],
        "catalog_description": (
            "A hands-on course in edge AI deployment using the NVIDIA Jetson Orin Nano 8 GB. "
            "Students configure the Jetson platform, optimize deep learning models with TensorRT, "
            "build computer vision pipelines using OpenCV and PyTorch, and deploy production-grade "
            "AI inference workloads at the network edge. Topics include JetPack SDK, CUDA acceleration, "
            "generative media pipelines, and thermal/power management for sustained deployment."
        ),
        "textbooks": [
            {
                "title": "Programming PyTorch for Deep Learning",
                "authors": "Ian Pointer",
                "edition": "O'Reilly, 2019",
                "isbn": "978-1-492-04553-9",
            },
            {
                "title": "NVIDIA Jetson Orin Developer Guide",
                "authors": "NVIDIA Corporation",
                "edition": "docs.nvidia.com/jetson, current edition",
                "isbn": "N/A (online documentation)",
            },
        ],
        "faculty": {
            "role": "Course Coordinator",
            "note": "Instruction delivered by NVIDIA Deep Learning Institute (DLI) Certified faculty of the Department of Artificial Intelligence & Robotics.",
        },
    },
    "databases": {
        "title": "Database Systems",
        "icon": "🗄️",
        "description": "Design and query relational and NoSQL databases using SQL, PostgreSQL, and MongoDB.",
        "color": "amber",
        "sequence": 4,
        "year": 2,
        "prev_course": "python",
        "next_course": "softeng",
        "builds_on": [
            "Python programming (CS 215) — database drivers, ORMs, and data-processing scripts are written in Python",
            "Linux command-line (SYS 202) — database servers run on Linux; psql and mongosh CLI tools are used for admin",
        ],
        "leads_to": "Software Engineering (CS 320) and Cybersecurity (SEC 301), where data modeling and secure storage are central design concerns",
        "course_number": "CS 310",
        "credits": 3,
        "lab_credits": 1,
        "department": "Department of Computer Science & Software Engineering",
        "prerequisites": ["Python Programming (CS 215)", "Introduction to Linux (SYS 202)"],
        "catalog_description": (
            "A rigorous introduction to database theory and practice. "
            "Topics include the relational model, SQL (DDL, DML, DCL, TCL), "
            "query optimization and indexing, normalization through BCNF, transaction management "
            "(ACID properties), and NoSQL paradigms (document stores, key-value, columnar, graph). "
            "Laboratory sessions use PostgreSQL, SQLite, and MongoDB. "
            "Students design and implement a multi-table normalized schema and a Python-backed API "
            "that serves data to a REST client."
        ),
        "textbooks": [
            {
                "title": "Database System Concepts",
                "authors": "Abraham Silberschatz, Henry F. Korth & S. Sudarshan",
                "edition": "7th ed., McGraw-Hill, 2020",
                "isbn": "978-0-07-802215-9",
            },
            {
                "title": "Learning SQL",
                "authors": "Alan Beaulieu",
                "edition": "3rd ed., O'Reilly, 2020",
                "isbn": "978-1-492-05759-4",
            },
        ],
        "faculty": {
            "role": "Course Coordinator",
            "note": "Instruction delivered by faculty of the Department of Computer Science & Software Engineering.",
        },
    },
    "cybersecurity": {
        "title": "Cybersecurity",
        "icon": "🔐",
        "description": "Master threat analysis, cryptography, network defence, penetration testing, and incident response.",
        "color": "red",
        "sequence": 7,
        "year": 3,
        "prev_course": "cisco",
        "next_course": "cloud",
        "builds_on": [
            "Networking fundamentals (NET 201) — attack surfaces map directly to the OSI stack; TCP/IP knowledge is assumed in every lab",
            "Linux system administration (SYS 202) — most offensive and defensive tools run on Linux",
            "Python programming (CS 215) — exploit scripts, automation, and analysis tools are written in Python",
        ],
        "leads_to": "Cloud Computing & DevOps (CS 401), where secure-by-design infrastructure and zero-trust architecture are applied at scale",
        "course_number": "SEC 301",
        "credits": 3,
        "lab_credits": 1,
        "department": "Department of Cybersecurity & Information Assurance",
        "prerequisites": [
            "Networking Fundamentals (NET 201)",
            "Introduction to Linux (SYS 202)",
            "Python Programming (CS 215)",
        ],
        "catalog_description": (
            "A comprehensive introduction to cybersecurity principles and practice. "
            "Topics include the CIA triad, common attack vectors (OWASP Top 10, MITRE ATT&CK), "
            "symmetric and asymmetric cryptography, PKI and TLS, network security controls "
            "(firewalls, IDS/IPS, VPNs), ethical hacking methodology (reconnaissance, scanning, "
            "exploitation, post-exploitation, reporting), and incident response procedures. "
            "Laboratory sessions use Kali Linux, Wireshark, Metasploit, and Burp Suite in "
            "isolated lab environments. This course prepares students for the CompTIA Security+ "
            "and Certified Ethical Hacker (CEH) examinations."
        ),
        "textbooks": [
            {
                "title": "CompTIA Security+ Study Guide",
                "authors": "Mike Chapple & David Seidl",
                "edition": "9th ed., Sybex, 2023",
                "isbn": "978-1-119-90671-7",
            },
            {
                "title": "The Web Application Hacker's Handbook",
                "authors": "Dafydd Stuttard & Marcus Pinto",
                "edition": "2nd ed., Wiley, 2011",
                "isbn": "978-1-118-02647-2",
            },
        ],
        "faculty": {
            "role": "Course Coordinator",
            "note": "Instruction delivered by CompTIA Security+ and CEH Certified faculty of the Department of Cybersecurity & Information Assurance.",
        },
    },
    "cloud": {
        "title": "Cloud & DevOps",
        "icon": "☁️",
        "description": "Deploy scalable applications using AWS/GCP/Azure, Docker, Kubernetes, Terraform, and CI/CD pipelines.",
        "color": "sky",
        "sequence": 8,
        "year": 4,
        "prev_course": "cybersecurity",
        "next_course": "jetson",
        "builds_on": [
            "Linux system administration (SYS 202) — every cloud instance, container, and serverless runtime runs Linux",
            "Networking fundamentals (NET 201) — VPCs, subnets, security groups, and load balancers extend your subnetting and routing knowledge",
            "Python programming (CS 215) — Terraform, Ansible, and SDK automation are written in Python or HCL",
            "Cybersecurity (SEC 301) — IAM policies, TLS, and zero-trust principles are applied throughout every cloud deployment",
        ],
        "leads_to": "Edge AI Development (AI 340), where cloud infrastructure skills underpin model registries, remote inference endpoints, and fleet OTA updates",
        "course_number": "CS 401",
        "credits": 3,
        "lab_credits": 2,
        "department": "Department of Computer Science & Software Engineering",
        "prerequisites": [
            "Cybersecurity Fundamentals (SEC 301)",
            "Networking Fundamentals (NET 201)",
            "Python Programming (CS 215)",
        ],
        "catalog_description": (
            "A hands-on course in cloud computing and modern DevOps engineering. "
            "Students provision infrastructure on AWS, Azure, and GCP using the console, CLI, "
            "and Terraform (Infrastructure as Code). Topics include compute (EC2, VMs, Cloud Run), "
            "managed databases, object storage, IAM and least-privilege design, containerization "
            "with Docker, container orchestration with Kubernetes, and CI/CD pipeline construction "
            "with GitHub Actions. Students complete a capstone deploying a microservices application "
            "through a full automated pipeline to a Kubernetes cluster. "
            "Prepares students for the AWS Solutions Architect Associate and "
            "Certified Kubernetes Administrator (CKA) examinations."
        ),
        "textbooks": [
            {
                "title": "Cloud Native Patterns",
                "authors": "Cornelia Davis",
                "edition": "Manning, 2019",
                "isbn": "978-1-617-29451-5",
            },
            {
                "title": "Kubernetes in Action",
                "authors": "Marko Lukša",
                "edition": "2nd ed., Manning, 2022",
                "isbn": "978-1-617-29752-3",
            },
        ],
        "faculty": {
            "role": "Course Coordinator",
            "note": "Instruction delivered by AWS Certified Solutions Architect and CKA Certified faculty of the Department of Computer Science & Software Engineering.",
        },
    },
    "softeng": {
        "title": "Software Engineering",
        "icon": "⚙️",
        "description": "Apply agile methodologies, design patterns, Git workflows, automated testing, and CI/CD to build production software.",
        "color": "slate",
        "sequence": 5,
        "year": 2,
        "prev_course": "databases",
        "next_course": "cisco",
        "builds_on": [
            "Python programming (CS 215) — all examples use Python; students write unit tests and apply OOP design patterns in Python",
            "Database systems (CS 310) — software systems persist state; you will apply schema design and ORM patterns here",
        ],
        "leads_to": "Cybersecurity (SEC 301) and Cloud & DevOps (CS 401), where software engineering practices — testing, CI/CD, code review — are prerequisites",
        "course_number": "CS 320",
        "credits": 3,
        "lab_credits": 1,
        "department": "Department of Computer Science & Software Engineering",
        "prerequisites": ["Python Programming (CS 215)", "Database Systems (CS 310)"],
        "catalog_description": (
            "An intermediate course in software engineering principles and professional practice. "
            "Topics include the software development lifecycle (SDLC), agile and Scrum methodology, "
            "version control with Git and GitHub (branching strategies, pull requests, code review), "
            "object-oriented design and SOLID principles, GoF design patterns (Creational, Structural, "
            "Behavioural), automated testing (unit, integration, end-to-end), test-driven development (TDD), "
            "static analysis and code quality tools, and CI/CD pipeline fundamentals. "
            "Students complete a team project following an agile sprint cycle and submit a tested, "
            "reviewed, and automatically deployed application."
        ),
        "textbooks": [
            {
                "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
                "authors": "Robert C. Martin",
                "edition": "Prentice Hall, 2008",
                "isbn": "978-0-13-235088-4",
            },
            {
                "title": "Design Patterns: Elements of Reusable Object-Oriented Software",
                "authors": "Gang of Four (Gamma, Helm, Johnson & Vlissides)",
                "edition": "Addison-Wesley, 1994",
                "isbn": "978-0-20-163361-5",
            },
        ],
        "faculty": {
            "role": "Course Coordinator",
            "note": "Instruction delivered by industry-certified faculty of the Department of Computer Science & Software Engineering.",
        },
    },
}

# ---------------------------------------------------------------------------
# Jinja2 filter
# ---------------------------------------------------------------------------

@app.template_filter("markdown_to_html")
def markdown_to_html(text):
    """Convert a markdown string to safe HTML."""
    if not text:
        return ""

    mermaid_blocks = []

    def _capture_mermaid(match):
        idx = len(mermaid_blocks)
        mermaid_blocks.append(match.group(1).strip())
        return f"MERMAID_BLOCK_{idx}"

    processed_text = MERMAID_BLOCK_RE.sub(_capture_mermaid, text)
    rendered = md.markdown(
        processed_text,
        extensions=MARKDOWN_EXTENSIONS,
    )

    for idx, block in enumerate(mermaid_blocks):
        token = f"MERMAID_BLOCK_{idx}"
        diagram_html = f'<div class="mermaid">{block}</div>'
        rendered = rendered.replace(f"<p>{token}</p>", diagram_html)
        rendered = rendered.replace(token, diagram_html)

    rendered = bleach.clean(
        rendered,
        tags=BLEACH_ALLOWED_TAGS,
        attributes=BLEACH_ALLOWED_ATTRS,
        protocols=["http", "https", "mailto", "data"],
        strip=True,
    )

    # Bleach escapes Mermaid operators (like -->); restore only inside Mermaid blocks.
    rendered = re.sub(
        r'<div class="mermaid">(.*?)</div>',
        lambda m: f'<div class="mermaid">{unescape(m.group(1))}</div>',
        rendered,
        flags=re.DOTALL,
    )

    return Markup(
        rendered
    )


# ---------------------------------------------------------------------------
# Content helpers – lessons
# ---------------------------------------------------------------------------

def load_lessons(category):
    """Load all lessons for a given category from YAML files."""
    category_dir = os.path.join(config.CONTENT_DIR, category)
    lessons = []
    if not os.path.isdir(category_dir):
        return lessons
    for filename in sorted(os.listdir(category_dir)):
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            filepath = os.path.join(category_dir, filename)
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)
                if data:
                    data["slug"] = filename.replace(".yaml", "").replace(".yml", "")
                    lessons.append(data)
    return lessons


def load_lesson(category, slug):
    """Load a single lesson by category and slug."""
    for ext in (".yaml", ".yml"):
        filepath = os.path.join(config.CONTENT_DIR, category, slug + ext)
        if os.path.isfile(filepath):
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)
                if data:
                    data["slug"] = slug
                    return data
    return None


def build_fast_track_sections(category, lesson_title):
    """Generate extra advanced sections to lengthen lessons and increase pace."""
    common_sections = [
        {
            "heading": "Fast-Track Sprint (45 Minutes)",
            "content": f"""
Move quickly through **{lesson_title}** with this timed sprint:

1. **10 min**: Re-state the core concept in your own words and list 3 practical use-cases.
2. **15 min**: Build or run a minimal working demo that proves the concept end-to-end.
3. **10 min**: Add one failure test and one performance check.
4. **10 min**: Write a short technical debrief with tradeoffs and next improvements.

Pace rule:
- If you are blocked for more than 5 minutes, reduce scope and keep moving.
- Ship a working baseline first, then optimize.
""",
        },
        {
            "heading": "Challenge Ladder (Bronze to Gold)",
            "content": """
Use this challenge progression to deepen mastery quickly:

- **Bronze**: Reproduce baseline behavior from the lesson exactly.
- **Silver**: Add observability (logs, metrics, or validation checks).
- **Gold**: Improve speed, reliability, or clarity with a measurable result.

Score yourself after each rung:
- Correctness (0-5)
- Speed of delivery (0-5)
- Debugging quality (0-5)
- Communication quality (0-5)

Target: at least **15/20** before advancing.
""",
        },
    ]

    category_sections = {
        "linux": [
            {
                "heading": "Linux Deep Ops Drill",
                "interactive": "practice_vm",
                "content": """
Run this accelerated admin drill on a practice VM:

```bash
# 1) Create sandbox
mkdir -p ~/lab/{logs,data,bin} && cd ~/lab

# 2) Generate files and inspect metadata
for i in {1..5}; do echo "entry-$i" >> logs/app.log; done
ls -lah logs && stat logs/app.log

# 3) Search and filter quickly
grep -n "entry" logs/app.log | wc -l
find ~/lab -type f -name "*.log"

# 4) Permission hardening
chmod 640 logs/app.log
sudo chown "$USER":"$USER" logs/app.log
```

Deliverable:
- A short report listing commands used, why they were chosen, and one safer alternative.
""",
            },
            {
                "heading": "Incident Response Mini-Scenario",
                "content": """
Scenario: a service fails at startup after a config change.

Response sequence:
1. Verify process and port state.
2. Inspect latest logs and isolate first meaningful error.
3. Roll back the minimal change.
4. Validate service health and create a prevention checklist.

Focus on decision speed: you should produce a first diagnosis in under 8 minutes.
""",
            },
        ],
        "networking": [
            {
                "heading": "Packet Reasoning Lab",
                "content": """
Use fast packet-level reasoning for each concept in this lesson:

1. Identify source/destination addresses.
2. Identify encapsulation at each layer.
3. Predict next hop behavior.
4. Explain where the packet could fail and how to prove it.

Template:
```text
Flow:
Host A -> Switch -> Router -> ISP -> Service

Checks:
- L2: MAC table / VLAN membership
- L3: route lookup / gateway correctness
- L4: port reachability
```

Deliverable:
- One complete packet walk with a verified failure point and fix.
""",
            },
            {
                "heading": "Time-Boxed Subnet and Routing Set",
                "content": """
Complete 5 rapid problems in 20 minutes:

- 2 subnetting tasks with host-range validation
- 2 route selection tasks (longest-prefix match)
- 1 troubleshooting task with overlapping routes

Rule: show both the answer and the calculation path.
""",
            },
        ],
        "cisco": [
            {
                "heading": "Cisco CLI Speed Lab",
                "content": """
Practice high-frequency IOS workflow patterns:

```text
enable
configure terminal
interface g0/1
description Uplink-to-Core
switchport mode trunk
switchport trunk allowed vlan 10,20,30
end
write memory
show run interface g0/1
show interfaces trunk
```

Target outcomes:
- Correct syntax without tab-complete dependency
- Verification commands after every major change
- Rollback command prepared before risky edits
""",
            },
            {
                "heading": "Change Window Simulation",
                "content": """
Simulate a 30-minute production change window:

1. Pre-check (baseline state capture)
2. Change application (small, reversible steps)
3. Validation (control-plane + data-plane)
4. Backout trigger criteria
5. Post-change summary

This builds real-world speed with safe execution discipline.
""",
            },
        ],
        "python": [
            {
                "heading": "Python Performance and Reliability Pass",
                "content": """
Take a lesson script from working to production-grade:

1. Add type hints for core functions.
2. Add input validation and explicit exceptions.
3. Add structured logging for key transitions.
4. Add 3 focused tests: happy path, edge case, failure case.

Example scaffold:
```python
def parse_record(line: str) -> dict:
    if not line.strip():
        raise ValueError("empty line")
    # parse and validate fields
    return {"ok": True}
```

Measure improvement by reduced debug time and clearer failure messages.
""",
            },
            {
                "heading": "Automation Sprint",
                "content": """
Build a tiny automation utility in under 40 minutes:

- Input: file or API response
- Transform: parse, filter, normalize
- Output: human-readable report and machine-readable JSON

Stretch goal:
- Add retry logic and timeout handling for external calls.
""",
            },
        ],
        "jetson": [
            {
                "heading": "Edge Optimization Sprint",
                "content": """
Push the lesson artifact toward real deployment constraints:

1. Measure baseline latency and memory.
2. Reduce overhead (model warmup, pre-allocation, batch tuning).
3. Re-measure and document delta.

Benchmark template:
```text
Metric        Baseline   Optimized   Delta
Latency p95   120 ms     84 ms       -30%
RAM usage     2.1 GB     1.7 GB      -19%
```

Aim for one measurable improvement, not theoretical tuning.
""",
            },
            {
                "heading": "Deployment Readiness Checklist",
                "content": """
Before shipping on Jetson, confirm:

- Deterministic startup path
- Health endpoints and watchdog behavior
- Graceful degradation when GPU is unavailable
- Resource limits and thermal behavior under sustained load
- Reproducible setup instructions

Deliver a one-page readiness note with risks and mitigations.
""",
            },
        ],
        "databases": [
            {
                "heading": "SQL Query Sprint",
                "content": """
Practice writing correct, efficient SQL under time pressure:

```sql
-- 1) Basic SELECT with filtering and ordering (3 min)
SELECT customer_id, order_total
FROM orders
WHERE order_date >= '2024-01-01'
ORDER BY order_total DESC
LIMIT 10;

-- 2) JOIN across three tables (5 min)
SELECT c.name, COUNT(o.id) AS order_count, SUM(o.total) AS revenue
FROM customers c
JOIN orders o ON c.id = o.customer_id
JOIN order_items oi ON o.id = oi.order_id
GROUP BY c.id, c.name
HAVING COUNT(o.id) > 2;

-- 3) Subquery for relative analysis (5 min)
SELECT product_name, price
FROM products
WHERE price > (SELECT AVG(price) FROM products);
```

Target: all three queries correct within 15 minutes.
""",
            },
            {
                "heading": "Schema Design Challenge",
                "content": """
Design a normalized database schema for the following scenario in 20 minutes:

**E-commerce Order System:**
- Customers place orders containing multiple products
- Products belong to categories
- Orders have statuses (pending, shipped, delivered, cancelled)
- Each order line tracks quantity and unit price at time of purchase

Deliverables:
1. Entity-Relationship (ER) diagram using Crow's Foot notation
2. DDL (`CREATE TABLE` statements) for all entities
3. At least one index justified by a query pattern
4. Explanation of normalization decisions (1NF → 3NF)
""",
            },
        ],
        "cybersecurity": [
            {
                "heading": "Threat Modelling Sprint",
                "content": """
Apply the STRIDE threat model to a simple web application in 20 minutes:

```text
STRIDE Categories:
S — Spoofing identity
T — Tampering with data
R — Repudiation (denying actions)
I — Information disclosure
D — Denial of service
E — Elevation of privilege
```

For each category:
1. Identify one realistic threat to the system
2. Rate likelihood (1-5) and impact (1-5)
3. Propose one mitigation control

Deliverable: a 6-row STRIDE table with threats and controls.
""",
            },
            {
                "heading": "Network Packet Analysis Lab",
                "content": """
Analyse a packet capture (PCAP) file to answer forensic questions:

```bash
# Filter for suspicious traffic patterns
tcpdump -r capture.pcap -n 'tcp[tcpflags] & tcp-syn != 0'

# Extract DNS queries
tshark -r capture.pcap -Y "dns.flags.response == 0" -T fields -e dns.qry.name

# Look for credentials in cleartext
strings capture.pcap | grep -i "password\|passwd\|secret"
```

Analysis checklist:
- Identify source/destination IP pairs with highest volume
- Flag any unencrypted credential transmissions
- Identify port scan patterns (SYN without ACK)
- Document findings in a brief incident report
""",
            },
        ],
        "cloud": [
            {
                "heading": "Infrastructure as Code Sprint",
                "content": """
Provision a complete application stack using Terraform in 30 minutes:

```hcl
# main.tf — VPC + EC2 + Security Group skeleton
provider "aws" {
  region = "us-east-1"
}

resource "aws_vpc" "app_vpc" {
  cidr_block = "10.0.0.0/16"
  tags = { Name = "app-vpc" }
}

resource "aws_security_group" "web_sg" {
  vpc_id = aws_vpc.app_vpc.id
  ingress {
    from_port = 443; to_port = 443; protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

Objectives:
1. Define a VPC with public and private subnets
2. Add a security group allowing only HTTPS inbound
3. Create an EC2 instance in the public subnet
4. Output the public IP address
5. `terraform plan` must show zero errors
""",
            },
            {
                "heading": "CI/CD Pipeline Lab",
                "content": """
Design a complete GitHub Actions pipeline for a Python application:

```yaml
name: CI/CD Pipeline
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --cov
  build-and-push:
    needs: test
    if: github.ref == 'refs/heads/main'
    steps:
      - run: docker build -t myapp:${{ github.sha }} .
      - run: docker push registry/myapp:${{ github.sha }}
```

Complete the pipeline to:
1. Run lint (flake8) before tests
2. Build and push Docker image on main only
3. Deploy to Kubernetes using kubectl rollout
""",
            },
        ],
        "softeng": [
            {
                "heading": "Code Review Sprint",
                "content": """
Review this Python function against SOLID principles and clean code standards:

```python
def process(d, t, s=True):
    result = []
    for item in d:
        if s == True:
            if item['status'] == 'active':
                result.append({'id': item['id'], 'name': item['name'],
                               'total': item['price'] * t})
        else:
            result.append({'id': item['id'], 'name': item['name'],
                           'total': item['price'] * t})
    return result
```

Identify issues in these categories:
1. **Naming** — are names self-documenting?
2. **Single Responsibility** — does the function do one thing?
3. **DRY** — is there duplication?
4. **Type Hints** — are inputs/outputs typed?
5. **Tests** — write one unit test for the current version and one for your refactored version.

Deliverable: refactored function + two tests.
""",
            },
            {
                "heading": "TDD Mini-Cycle",
                "content": """
Practice Red-Green-Refactor in 25 minutes:

**Requirement:** Write a `BankAccount` class with:
- `deposit(amount)` — adds to balance
- `withdraw(amount)` — subtracts; raises `InsufficientFunds` if overdraft
- `balance` property — returns current balance

Cycle:
1. **Red**: write a failing test for `deposit`
2. **Green**: write minimum code to pass it
3. **Refactor**: clean up
4. Repeat for `withdraw` (happy path)
5. Repeat for `withdraw` (overdraft raises exception)
6. Achieve 100% branch coverage with `pytest --cov`
""",
            },
        ],
    }

    return common_sections + category_sections.get(category, [])


# ---------------------------------------------------------------------------
# Content helpers – assignments
# ---------------------------------------------------------------------------

ASSIGNMENTS_DIR = os.path.join(os.path.dirname(__file__), "assignments")


def load_assignments(category):
    """Load all assignments for a given category from YAML files."""
    category_dir = os.path.join(ASSIGNMENTS_DIR, category)
    assignments = []
    if not os.path.isdir(category_dir):
        return assignments
    for filename in sorted(os.listdir(category_dir)):
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            filepath = os.path.join(category_dir, filename)
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)
                if data:
                    data["slug"] = filename.replace(".yaml", "").replace(".yml", "")
                    assignments.append(data)
    return assignments


def load_assignment(category, slug):
    """Load a single assignment by category and slug."""
    for ext in (".yaml", ".yml"):
        filepath = os.path.join(ASSIGNMENTS_DIR, category, slug + ext)
        if os.path.isfile(filepath):
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)
                if data:
                    data["slug"] = slug
                    return data
    return None


# ---------------------------------------------------------------------------
# Routes – lessons
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    category_data = {}
    for key, meta in CATEGORIES.items():
        lessons = load_lessons(key)
        category_data[key] = {**meta, "lesson_count": len(lessons)}
    ordered = sorted(category_data.values(), key=lambda c: c.get("sequence", 99))
    return render_template("index.html", categories=category_data, ordered_courses=ordered)


@app.route("/learning-path")
def learning_path():
    category_data = {}
    for key, meta in CATEGORIES.items():
        lessons = load_lessons(key)
        category_data[key] = {**meta, "key": key, "lesson_count": len(lessons)}
    ordered = sorted(category_data.values(), key=lambda c: c.get("sequence", 99))
    return render_template("learning_path.html", ordered_courses=ordered, categories=category_data)


@app.route("/category/<category>")
def category(category):
    if category not in CATEGORIES:
        return render_template("404.html"), 404
    meta = CATEGORIES[category]
    lessons = load_lessons(category)
    prev_key = meta.get("prev_course")
    next_key = meta.get("next_course")
    prev_cat = CATEGORIES.get(prev_key) if prev_key else None
    next_cat = CATEGORIES.get(next_key) if next_key else None
    return render_template(
        "category.html",
        category=category,
        meta=meta,
        lessons=lessons,
        prev_course_key=prev_key,
        next_course_key=next_key,
        prev_cat=prev_cat,
        next_cat=next_cat,
    )


@app.route("/lesson/<category>/<slug>")
def lesson(category, slug):
    if category not in CATEGORIES:
        return render_template("404.html"), 404
    data = load_lesson(category, slug)
    if not data:
        return render_template("404.html"), 404

    extra_sections = build_fast_track_sections(category, data.get("title", "Lesson"))
    data["sections"] = data.get("sections", []) + extra_sections

    # Pre-render section markdown to HTML to avoid template/filter variance.
    sections = data.get("sections", [])
    for section in sections:
        section["content_html"] = markdown_to_html(section.get("content", ""))
    meta = CATEGORIES[category]
    lessons = load_lessons(category)
    current_index = next((i for i, l in enumerate(lessons) if l["slug"] == slug), None)
    prev_lesson = lessons[current_index - 1] if current_index and current_index > 0 else None
    next_lesson = (
        lessons[current_index + 1]
        if current_index is not None and current_index < len(lessons) - 1
        else None
    )
    return render_template(
        "lesson.html",
        lesson=data,
        meta=meta,
        category=category,
        prev_lesson=prev_lesson,
        next_lesson=next_lesson,
    )


# ---------------------------------------------------------------------------
# Routes – assignments
# ---------------------------------------------------------------------------

@app.route("/assignments")
def assignments_home():
    category_data = {}
    for key, meta in CATEGORIES.items():
        items = load_assignments(key)
        category_data[key] = {**meta, "assignment_count": len(items)}
    return render_template("assignments_home.html", categories=category_data)


@app.route("/assignments/<category>")
def assignments(category):
    if category not in CATEGORIES:
        return render_template("404.html"), 404
    meta = CATEGORIES[category]
    items = load_assignments(category)
    return render_template(
        "assignments.html", category=category, meta=meta, assignments=items
    )


@app.route("/assignment/<category>/<slug>")
def assignment(category, slug):
    if category not in CATEGORIES:
        return render_template("404.html"), 404
    data = load_assignment(category, slug)
    if not data:
        return render_template("404.html"), 404
    meta = CATEGORIES[category]
    all_assignments = load_assignments(category)
    current_index = next(
        (i for i, a in enumerate(all_assignments) if a["slug"] == slug), None
    )
    prev_assignment = (
        all_assignments[current_index - 1]
        if current_index and current_index > 0
        else None
    )
    next_assignment = (
        all_assignments[current_index + 1]
        if current_index is not None and current_index < len(all_assignments) - 1
        else None
    )
    return render_template(
        "assignment.html",
        assignment=data,
        meta=meta,
        category=category,
        prev_assignment=prev_assignment,
        next_assignment=next_assignment,
    )


# ---------------------------------------------------------------------------
# API – AI assistant
# ---------------------------------------------------------------------------

@app.route("/assistant")
def assistant():
    return render_template("assistant.html", categories=CATEGORIES)


@app.route("/instructor")
def instructor():
    return render_template("instructor.html", categories=CATEGORIES)


@app.route("/chat")
def chat():
    """Full-page AI chat interface (used by chat.js frontend)."""
    return render_template("chat.html", categories=CATEGORIES)


@app.route("/api/ask", methods=["POST"])
@limiter.limit("120/minute")
def ask():
    """AI assistant endpoint."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    if "message" not in data:
        return jsonify({"error": "Missing message field"}), 400

    user_message = data["message"].strip()
    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    context = data.get("context", "general")
    provider = data.get("provider")

    system_prompt = ai_providers.EDUCATION_SYSTEM_PROMPT
    if context and context != "general":
        subject = CATEGORIES.get(context, {}).get("title", context)
        system_prompt += f" The current learning context is: {subject}."

    try:
        answer = ai_providers.ask(user_message, system_prompt=system_prompt, provider=provider)
        return jsonify({"answer": answer})
    except ai_providers.ProviderError as exc:
        return jsonify({"error": str(exc)}), exc.status_code
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Unexpected server error: {exc}"}), 500


@app.route("/api/chat", methods=["POST"])
@limiter.limit("120/minute")
def chat_api():
    """Chat API endpoint used by the chat.js frontend."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    if "message" not in data:
        return jsonify({"error": "Missing message field"}), 400

    user_message = data["message"].strip()
    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    # Graceful fallback when no AI provider is configured
    if not ai_providers.get_available_providers():
        return jsonify(
            {
                "reply": (
                    "No AI provider is configured. Please set PERPLEXITY_API_KEY "
                    "(or OPENAI_API_KEY / GEMINI_API_KEY) in your .env file "
                    "to enable AI responses."
                )
            }
        ), 200

    category = data.get("category", "")
    provider = data.get("provider")
    settings = data.get("settings")

    system_prompt = ai_providers.EDUCATION_SYSTEM_PROMPT
    if category:
        subject = CATEGORIES.get(category.lower(), {}).get("title", category)
        system_prompt += f" The current learning context is: {subject}."

    try:
        payload = ai_providers.ask_chat(
            user_message,
            system_prompt=system_prompt,
            provider=provider,
            chat_options=settings,
        )
        return jsonify(payload)
    except ai_providers.ProviderError as exc:
        return jsonify({"error": str(exc)}), exc.status_code
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Unexpected server error: {exc}"}), 500


def _sse(event, data):
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.route("/api/chat/stream", methods=["POST"])
@limiter.limit("120/minute")
def chat_stream_api():
    """Streaming chat endpoint (SSE over POST)."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    if "message" not in data:
        return jsonify({"error": "Missing message field"}), 400

    user_message = data["message"].strip()
    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    category = data.get("category", "")
    provider = data.get("provider")
    settings = data.get("settings")

    system_prompt = ai_providers.EDUCATION_SYSTEM_PROMPT
    if category:
        subject = CATEGORIES.get(category.lower(), {}).get("title", category)
        system_prompt += f" The current learning context is: {subject}."

    def generate():
        try:
            if not ai_providers.get_available_providers():
                fallback = (
                    "No AI provider is configured. Please set PERPLEXITY_API_KEY "
                    "(or OPENAI_API_KEY / GEMINI_API_KEY) in your .env file "
                    "to enable AI responses."
                )
                yield _sse("delta", {"text": fallback})
                yield _sse("done", {"reply": fallback, "provider": "none"})
                return

            for event in ai_providers.stream_chat(
                user_message,
                system_prompt=system_prompt,
                provider=provider,
                chat_options=settings,
            ):
                yield _sse(event.get("event", "delta"), event.get("data", {}))
        except ai_providers.ProviderError as exc:
            yield _sse("error", {"message": str(exc), "status": exc.status_code})
        except Exception as exc:  # noqa: BLE001
            yield _sse("error", {"message": f"Unexpected server error: {exc}", "status": 500})

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/instructor", methods=["POST"])
@limiter.limit("120/minute")
def instructor_api():
    """
    Instructor agent endpoint supporting multi-turn conversations.

    Expected JSON body:
    {
        "messages": [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."},
            {"role": "user", "content": "..."}
        ],
        "subject": "Linux",   // optional
        "provider": "openai"  // optional
    }

    Returns:
    {
        "reply": "..."
    }
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    messages = data.get("messages")
    if not messages or not isinstance(messages, list):
        return jsonify({"error": "Missing or invalid messages field"}), 400

    for msg in messages:
        if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
            return jsonify({"error": "Each message must have 'role' and 'content' fields"}), 400
        if msg["role"] not in ("user", "assistant"):
            return jsonify({"error": "Message role must be 'user' or 'assistant'"}), 400
        if not isinstance(msg["content"], str):
            return jsonify({"error": "Message content must be a string"}), 400

    if messages[-1]["role"] != "user":
        return jsonify({"error": "Last message must be from the user"}), 400

    last_content = messages[-1]["content"].strip()
    if not last_content:
        return jsonify({"error": "Last message content cannot be empty"}), 400

    if not ai_providers.get_available_providers():
        return jsonify(
            {
                "reply": (
                    "No AI provider is configured. Please set PERPLEXITY_API_KEY "
                    "(or OPENAI_API_KEY / GEMINI_API_KEY) in your .env file "
                    "to enable the instructor agent."
                )
            }
        ), 200

    subject = data.get("subject", "")
    provider = data.get("provider")
    if provider is not None and provider not in ai_providers.PROVIDER_LABELS:
        return jsonify({"error": f"Invalid provider. Choose from: {', '.join(ai_providers.PROVIDER_LABELS)}"}), 400

    try:
        reply = instructor_agent.ask(messages, subject=subject or None, provider=provider)
        return jsonify({"reply": reply})
    except ai_providers.ProviderError as exc:
        return jsonify({"error": str(exc)}), exc.status_code
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Unexpected server error: {exc}"}), 500


# ---------------------------------------------------------------------------
# API – assignment grading
# ---------------------------------------------------------------------------

@app.route("/api/grade", methods=["POST"])
@limiter.limit("60/minute")
def grade():
    """
    Grade an assignment submission.

    Expected JSON body:
    {
        "category": "networking",
        "slug": "01_osi_model_assignment",
        "answers": {
            "1": "user answer or selected option index as string",
            "2": "free-text answer",
            ...
        }
    }

    Returns:
    {
        "score": 70,
        "max_score": 100,
        "percentage": 70.0,
        "letter_grade": "C",
        "tasks": [
            {
                "id": 1,
                "type": "multiple_choice",
                "score": 10,
                "max_score": 10,
                "correct": true,
                "feedback": "Correct! ...",
                "ideal_answer": "..."
            },
            ...
        ],
        "overall_feedback": "..."
    }
    """
    body = request.get_json()
    if not body:
        return jsonify({"error": "Missing request body"}), 400

    category = body.get("category", "")
    slug = body.get("slug", "")
    answers = body.get("answers", {})

    if not category or not slug:
        return jsonify({"error": "Missing category or slug"}), 400

    assignment_data = load_assignment(category, slug)
    if not assignment_data:
        return jsonify({"error": "Assignment not found"}), 404

    tasks = assignment_data.get("tasks", [])
    graded_tasks = []
    total_score = 0
    total_max = 0

    open_tasks_to_grade = []  # collected for batch AI grading

    for task in tasks:
        task_id = str(task["id"])
        task_type = task.get("type", "short_answer")
        max_pts = task.get("points", 10)
        user_answer = answers.get(task_id, "").strip()

        total_max += max_pts

        if task_type == "multiple_choice":
            result = _grade_multiple_choice(task, user_answer, max_pts)
            total_score += result["score"]
            graded_tasks.append(result)
        else:
            # Defer open-ended tasks to AI grading
            open_tasks_to_grade.append((task, user_answer, max_pts))

    # AI-grade all open-ended tasks (requires API key)
    if open_tasks_to_grade:
        if not ai_providers.get_available_providers():
            # Graceful degradation: return pending results without AI score
            for task, user_answer, max_pts in open_tasks_to_grade:
                graded_tasks.append(
                    {
                        "id": task["id"],
                        "type": task.get("type"),
                        "score": 0,
                        "max_score": max_pts,
                        "correct": False,
                        "feedback": "AI grading is unavailable (no API key configured). Please review the ideal answer below.",
                        "ideal_answer": task.get("sample_answer", "See rubric."),
                        "pending": True,
                    }
                )
        else:
            subject = CATEGORIES.get(category, {}).get("title", category)
            for task, user_answer, max_pts in open_tasks_to_grade:
                try:
                    result = ai_providers.grade_open_ended(task, user_answer, max_pts, subject)
                    total_score += result["score"]
                    graded_tasks.append(result)
                except ai_providers.ProviderError as exc:
                    return jsonify({"error": str(exc)}), exc.status_code

    # Sort graded tasks by original task id order
    id_order = {str(t["id"]): i for i, t in enumerate(tasks)}
    graded_tasks.sort(key=lambda t: id_order.get(str(t["id"]), 999))

    percentage = round((total_score / total_max) * 100, 1) if total_max else 0
    letter_grade = _letter_grade(percentage)

    overall_feedback = _overall_feedback(percentage, graded_tasks)

    return jsonify(
        {
            "score": total_score,
            "max_score": total_max,
            "percentage": percentage,
            "letter_grade": letter_grade,
            "tasks": graded_tasks,
            "overall_feedback": overall_feedback,
        }
    )


def _grade_multiple_choice(task, user_answer, max_pts):
    """Grade a multiple-choice task locally (no AI needed)."""
    try:
        selected = int(user_answer)
    except (ValueError, TypeError):
        selected = -1

    correct_index = task.get("answer", -1)
    is_correct = selected == correct_index
    score = max_pts if is_correct else 0
    options = task.get("options", [])
    correct_text = options[correct_index] if 0 <= correct_index < len(options) else "N/A"

    return {
        "id": task["id"],
        "type": "multiple_choice",
        "score": score,
        "max_score": max_pts,
        "correct": is_correct,
        "feedback": (
            "✅ Correct! " + task.get("explanation", "")
            if is_correct
            else "❌ Incorrect. " + task.get("explanation", "")
        ),
        "ideal_answer": correct_text,
    }


def _letter_grade(percentage):
    if percentage >= 90:
        return "A"
    if percentage >= 80:
        return "B"
    if percentage >= 70:
        return "C"
    if percentage >= 60:
        return "D"
    return "F"


def _overall_feedback(percentage, graded_tasks):
    missed = [t for t in graded_tasks if not t.get("correct")]
    if percentage >= 90:
        return "Excellent work! You have a strong grasp of this material."
    if percentage >= 70:
        missed_str = ", ".join(str(t["id"]) for t in missed)
        return f"Good effort! Review the feedback on task(s) {missed_str} to strengthen your understanding."
    return (
        "Keep practicing! Review the lesson material and the ideal answers below, "
        "then try again once you feel more confident."
    )


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=config.DEBUG, host="0.0.0.0", port=5000)
