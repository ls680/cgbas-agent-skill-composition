# Cover letter

Dear Editor,

We submit the research paper “Repair the Boundary, Not the Skills: Contract-Guided Adapter Synthesis for LLM-Agent Skill Composition” for consideration in the *Journal of Systems and Software*.

The paper addresses a software-maintenance problem in reusable LLM-agent systems. A composition can fail at an interface even when its component Skills have individually successful provenance. We introduce Contract-Guided Boundary Adapter Synthesis (CGBAS), which compiles one diagnosed boundary adapter while leaving the component artifacts unchanged. The method combines typed rely/guarantee contracts, downstream liveness, and retained successful provenance to restore a missing witness prefix, specialize a consumer role, or guard a destructive call before execution.

The evaluation separates exposed development evidence from an identifier-disjoint confirmation cohort. It compares CGBAS with no repair, a contract-only local heuristic, whole-chain rollback under a locality constraint, and three revision-pinned open instruction models. Native ALFWorld and ScienceWorld execution, task-clustered inference, provenance audits, healthy controls, and action-cost reporting make the result directly relevant to software evolution, maintenance, and empirical evaluation of AI-enabled systems. The released artifact retains failed revisions, paired traces, locked inference, and replay instructions.

The manuscript is original and is not under consideration by another journal. All authors have reviewed the manuscript and approved its submission. There is no funding to declare and no competing interest. The study-specific code and records are openly available in Zenodo at https://doi.org/10.5281/zenodo.22855171 and in the public GitHub repository https://github.com/ls680/cgbas-agent-skill-composition. Third-party ALFWorld, ScienceWorld, and model-weight assets will be identified under their upstream licenses and will not be redistributed without permission.

Sincerely,

Liang Song  
Business School, Xi’an International University  
Xi’an 710077, Shaanxi, China  
Corresponding author: liangsong_1976@126.com  
ORCID: [0009-0002-6109-0639](https://orcid.org/0009-0002-6109-0639)

on behalf of

Zhai Jiabao  
School of Management and Economics, North China University of Water Resources and Electric Power  
Zhengzhou 450046, Henan, China  
zhaijiabao123@126.com
