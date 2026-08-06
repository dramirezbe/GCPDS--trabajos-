arXiv:2601.13118v1 [cs.SE] 19 Jan 2026

Guidelines to Prompt Large Language Models for Code Generation: An Empirical Characterization Alessandro Midolo∗

Alessandro Giagnorio∗

Fiorella Zampetti

alessandro.midolo@unict.it Dipartimento di Matematica e Informatica, University of Catania Catania, Italy

alessandro.giagnorio@usi.ch Software Institute – USI Università della Svizzera italiana Lugano, Switzerland

fzampetti@unisannio.it University of Sannio Benevento, Italy

Rosalia Tufano

Gabriele Bavota

Massimiliano Di Penta

rosalia.tufano@usi.ch Software Institute – USI Università della Svizzera italiana Lugano, Switzerland

gabriele.bavota@usi.ch Software Institute – USI Università della Svizzera italiana Lugano, Switzerland

dipenta@unisannio.it University of Sannio Benevento, Italy

## ABSTRACT

Large Language Models (LLMs) are extensively used nowadays for various software engineering tasks, primarily code generation. Previous research has shown how suitable prompt engineering could help developers improve their code generation prompts. However, so far, there are no specific guidelines driving developers to write suitable prompts for code generation. In this work, we derive and evaluate development-specific prompt optimization guidelines. We use an iterative, test-driven approach to automatically refine code generation prompts, and we analyze the outcome of this process to identify prompt improvement items that lead to test passes. We use such elements to elicit 10 guidelines for prompt improvement, related to better specifying I/O, pre/post conditions, providing examples, various types of details, or clarifying ambiguities. We conducted an assessment with 50 practitioners, who reported their usage of the elicited prompt improvement patterns, as well as their perceived usefulness. Our results have implications not only for practitioners and educators, but also for those creating LLM-aided software development tools.

## KEYWORDS

Large Language Models for Code Generation; Prompt Optimization

## INTRODUCTION

The use of Large Language Models (LLMs) is radically changing how developers perform various software engineering tasks, including code generation, (re) documentation, software quality improvement, learning new pieces of technology, and others [11, 20, 24, 49]. Focusing in particular on code generation, on the one hand, the task seems to be pretty straightforward, i.e., in several cases an LLM-based assistant is already able to generate a working solution based on a simple description of the task. At the same time, several studies [26, 29] outlined how some prompt elements, for example, the system prompt and the role played by the LLM—e.g., an expert Python or Java developer—may have a significant effect on the quality and correctness of the generated code. However, there may be several subtle elements that, if missed, may compromise the outcome of LLM-based code generation, such ∗ Both authors contributed equally to this research.

as the explanation of a method/function parameters, return values, pre- and post-conditions, or how exceptional cases are handled. To date, while general-purpose prompt engineering guidelines [37] and automated prompt optimization approaches exist [37, 45], there is a lack of specific guidelines and optimization tools targeting prompt engineering for software development. We conjecture that this is necessary because a software development prompt may need to contain very specific elements related to the technology, the specification, or the solution being requested, and this goes beyond general-purpose prompt optimization. In this paper, we are paving the way toward providing developers with guidelines to improve their code generation prompts. To achieve this goal, we started with code generation tasks from three Python code generation benchmarks: BigCodeBench [18], HumanEval+ [34], and MBPP+ [34]. We then created a simple prompt for four state-of-the-art LLMs—GPT-4o-mini [2], Llama 3.3 70B Instruct [3], Qwen2.5 72B Instruct [4], and DeepSeek Coder V2 Instruct [1]—and considered cases in which, over multiple iterations, the LLMs always generated code that led the benchmarks’ test cases to fail. Then, we used an automated, iterative approach that results in the LLM coming up with a prompt that is able to generate a test-passing code. After that, by manually analyzing the initial and final prompts and the test logs, we elicited a set of textual elements that the automated refinement added to the prompt to make the test cases pass. This allowed us to create a taxonomy of 10 code generation prompt improvement dimensions. To evaluate the obtained catalogue of prompt optimization guidelines, we conducted a survey study involving 50 practitioners from our professional network. In the study, we asked participants about (i) the extent to which they use, in their development activities, the prompt optimization patterns we elicited, as well as other patterns we did not mention, and (ii) their perceived usefulness of these optimization patterns. Results of the study indicated varying usage of such patterns, e.g., participants often tend to refine the I/O format or pre- and postconditions, while they less often use a “by example” approach or perform linguistic improvements. At the same time, they perceived particularly useful not only most of the optimization patterns they

already use, but also some, such as those related to adding I/O examples, that they tend to use less so far. The provided guidelines can be used, on the one hand, as a support for software practitioners and educators. On the other hand, in the future, they can lay the basis to create automated recommenders able to identify—also based on the context—missing elements from a prompt and suggest improvements for it.

## RELATED WORK

The growing complexity of LLM-based tasks has led to a surge in automated prompt optimization techniques. The recent survey by Ramnath et al. [46] systematically categorizes such techniques—including search-based methods, reinforcement learning, and human-feedback loops—while identifying open challenges like alignment and generalization. In particular, Pryzant et al. [45] introduce ProTeGi, which mimics gradient descent by generating natural-language feedback (textual gradients) to improve prompts iteratively. Wang et al. [51] take a more autonomous approach with PromptAgent, an LLM-powered agent that formulates prompt optimization as a planning problem, combining evaluation, goal decomposition, and self-improvement. Jinyang et al. [28] propose DDPT, which employs a diffusion model to learn continuous prompt embeddings optimized for code quality. While these techniques advance the automation of prompt refinement, they primarily operate as black boxes, offering limited transparency or actionable guidance to end users. In contrast, our work introduces a set of practical, empirically grounded guidelines, designed to support developers in crafting more effective prompts for code generation tasks, bridging the gap between sophisticated optimization methods and real-world LLM usage. Several works emphasize the role of human insights in improving prompt quality. Liu et al. [33] demonstrate how iterative, chainof-thought (CoT) prompt refinement can guide ChatGPT toward more accurate and context-aware outputs. Shin et al. [47] compare prompt engineering to fine-tuning for code-related tasks and find that interactive, conversational prompting—rather than static prompts—leads to superior results. Similarly, Zhang et al. [57] propose an interactive prompting framework for code snippet adaptation, showing that model-driven questioning followed by refinement yields more reliable transformations. However, procedural techniques such as CoT inherently require longer prompt sequences, increasing token usage, computational cost, and inference latency. Moreover, extended interactions have been shown to exacerbate hallucination tendencies in LLMs [13]. To address these limitations, our approach focuses on generating single, well-crafted prompts sufficiently detailed to elicit accurate and reliable responses—without relying on lengthy dialogue or iterative refinement. Beyond procedural guidance, human feedback has also been employed in prompt optimization. Lin et al. [32] introduce a preferencebased optimization framework that refines prompts based on human comparisons, bypassing the need for task-specific labels. This aligns with Wen et al. [53], who present a method for optimizing discrete (hard) prompts via gradient-based search, offering an interpretable and automatable alternative to manual crafting. Understanding the properties of effective prompts is critical for both design and optimization. Mao et al. [35] conduct a structured

analysis of prompt templates, revealing how layout, placeholders, and component composition impact instruction-following behavior. Lee et al. [27] introduce SPA, a syntactic analysis tool that predicts output characteristics from prompts without executing the LLM—enabling proactive prompt assessment. Fagădău et al. [19] focus on prompt features in code generation, showing that structural cues like I/O examples and method summaries strongly correlate with higher-quality outputs. Likewise, Wu et al. [55] analyze real-world ChatGPT usage patterns, linking prompt clarity and specificity with better developer outcomes. Our work complements this line of research, providing empirically-informed guidelines for prompt optimization in the context of code generation. Recent studies explore how prompts integrate into software development lifecycles. Liang et al. [30] argue that prompts function as first-class programmatic artifacts, noting developers’ challenges in debugging and understanding LLM behavior. Tafreshipour et al. [48] provide the first large-scale analysis of prompt evolution in codebases, uncovering common maintenance patterns and calling for better tooling and documentation. Complementing these artifact-level perspectives, Otten et al. [39] empirically investigate how software developers employ generative AI tools in practice. Their survey of professional programmers reveals diverse prompting strategies across coding tasks—from generation to debugging and review—and highlights that iterative, conversational prompting dominates real-world use. These findings underscore a broader gap: inadequate documentation and guidance for effectively using LLMs in real-world inference tasks. Our work addresses this need by offering structured guidelines that help developers craft high-quality prompts, bridging the usability divide between LLM capabilities and practical software engineering applications. In requirements engineering, Vogelsang et al. [50] analyze how linguistic smells in requirements affect LLM-driven traceability tasks, finding that poor formulations can impair performance in nuanced ways. Abukhalaf et al. [5] tackle prompt scalability in model-to-text tasks with PathOCL, which selects relevant UML paths to keep prompts concise and accurate. Several works highlight the importance of domain and context in crafting effective prompts. Peng et al. [42] propose TypeFix, which mines repair patterns to build domain-specific prompts for Python type error correction, outperforming rule- and learning-based baselines. Toufique et al. [6] enhance summarization by augmenting prompts with shallow semantic features, demonstrating that even lightweight program analysis improves LLM understanding. Peng et al. [41] introduce RepoSim, a benchmark for prompt strategies in code completion that captures realistic developer behavior. By leveraging contextual features like recent file edits and temporal patterns, RepoSim allows for more robust evaluation of prompt effectiveness under real-world conditions. Pister et al. [44] reinforce this view by presenting PromptSet, a dataset of developer-written prompts, and propose static analysis tools similar to linters to support prompt maintenance. Our work can further inform the design of these tools, thanks to the set of (validated) prompt-improvement guidelines we release.

Guidelines to Prompt Large Language Models for Code Generation: An Empirical Characterization

1,682 tasks

generation prompt (Po)

LLM

generated code

Code Optimization Process (sec. 3.4)

test suite 10 times

Guidelines Evaluation (sec. 3.7)

553 618 635 563

generation prompt (Po)

Identification of Guidelines (sec. 3.6)

code optimization prompt

LLM

generated code

test suite

guidelines

generation prompt (Po)

optimized prompt (Pf)

test suite

Prompt Optimization & Validation (sec. 3.5)

survey

50 participants

LLM

max 5 times

Code Generation through LLMs (sec. 3.3)

prompt optimization prompt

229 261 268 228

153 192 200 145 generated code

manual analysis

LLM

optimized prompt (Pf)

LLM

Figure 1: Methodology Overview

## STUDY DESIGN

The goal of this work is to establish guidelines for aiding developers in zero-shot LLM prompting in code generation. The perspective is that of developers aiming to leverage natural language specifications for source code generation using LLMs. The context consists of (i) development tasks from three benchmarks—BigCodeBench [18], HumanEval+ [34], MBPP+ [34]—and (ii) four state-of-the-art LLMs— GPT-4o mini [2], Llama 3.3 70B Instruct [3], Qwen2.5 72B Instruct [4], DeepSeek Coder V2 Instruct [1]. The study aims to address the following research questions: • RQ1 : What is the set of information to be included in the prompt to maximize the chance of success in a code generation task? RQ1 aims at identifying—through an automated prompt optimization process and a follow-up manual analysis—elements that might be necessary to add in a code generation task prompt to generate a correct code. • RQ2 : To what extent do the provided guidelines reflect the prompt improvement strategies used by practitioners? With this research question, we investigate the extent to which study participants have used, in their development activities, the prompt improvement guidelines identified in RQ1 . • RQ3 : To what extent do practitioners perceive the provided prompt improvement guidelines as useful? In RQ3 , we assess the study participants’ perceived usefulness of the provided guidelines, regardless of whether or not they use them.

### 3.1 Benchmark description

For our study, we leverage tasks from three benchmarks created for evaluating code generation models in Python: BigCodeBench [18], HumanEval+ [34], and MBPP+ [34]. BigCodeBench assesses LLMs on real-world programming tasks, focusing on complex reasoning and multi-library code generation. It comprises 1,140 Python tasks covering 139 libraries across seven domains, requiring models to compose solutions using diverse function calls. Each task includes an average of 5.6 test cases to ensure rigorous evaluation. HumanEval+ and MBPP+ extend HumanEval [12] and MBPP [9] respectively, by significantly increasing the number of test cases—80× more for HumanEval+ and 35× more for MBPP+. They feature 164

(HumanEval+) and 378 (MBPP+) coding tasks, evaluating functional correctness in LLM-generated code.

### 3.2 Methodology overview

Figure 1 provides an overview of our methodology. For each benchmark’s task and each LLM independently, we ask the LLM ten times to generate a valid code implementation. We then select the coding tasks for which the LLM always failed to generate a correct implementation (according to test execution) and start an optimization process guiding the LLM to generate the correct code based on the test results. If, within a maximum number of iterations, the LLM manages to output a correct implementation, this leads to a triplet <𝑃𝑜 , [𝐶 𝑤 ], 𝐶𝑐 >, where: (i) 𝑃𝑜 is the original code generation prompt provided in the benchmark; [𝐶 𝑤 ] is a set of wrong implementations outputted by the LLM when prompted with 𝑃𝑜 during the run of the iterations, with each (wrong) implementation paired with the errors printed by the tests; and (iii) 𝐶𝑐 is the fixed version of the code that the LLM generated when we showed it the errors reported by the tests. Such a triplet is finally provided to the LLM, asking it to automatically revise 𝑃𝑜 to produce a “fixed” prompt (𝑃 𝑓 ) which is likely to generate 𝐶𝑐 (i.e., the correct implementation). The generated 𝑃 𝑓 is then prompted to the LLM to verify whether it actually results in a correct implementation. If this is the case, such a process provides us with pairs <𝑃𝑜 , 𝑃 𝑓 > (i.e., original and fixed prompt) which we manually inspect, coming up with a catalogue of prompt optimizations implemented by the LLMs. Such a catalogue has been finally validated in a human study with practitioners. Note that the whole procedure we use to generate 𝑃 𝑓 is not meant to be an automated process used by developers in practice, since it assumes the availability of test execution results, which are often not available during code generation. The procedure is meant to automatically build a dataset of prompt optimizations to be manually inspected in our study. In the following, we detail the main steps of our methodology.

### 3.3 Code Generation through LLMs

The initial phase of our study focuses on source code generation using four state-of-the-art LLMs: GPT-4o mini [2], Llama 3.3 70B Instruct [3], Qwen2.5 72B Instruct [4], and DeepSeek Coder V2

Instruct [1]. We selected these models because recent studies have demonstrated their effectiveness in various software engineering applications [17, 21, 22, 56]. While other, even more performant models could be used, these models proved to be suitable for our purpose, i.e., to iteratively optimize code to make test passing, finally leading to an optimized prompt. As input to the LLMs, we adopt the prompts provided in the subject datasets (i.e., BigCodeBench, HumanEval+, and MBPP+), which consist of the method signature and its docstring. The signature is crucial to ensure that the generated method can be executed within the test suite without issues related to the method or parameter names. Generating the Code. Following recent studies [15, 16], we performed the generation process with zero temperature and a fixed seed. Lowering the temperature reduces nondeterminism compared to the default configuration [40], and has been shown to improve performance in code generation tasks [8, 14]. However, since the models do not guarantee full determinism even at low temperatures, we generated ten outputs for each LLM and for each task. Each generated code has then been validated against the related test suite. All the coding tasks for which each LLM always generated test-failing solutions are kept for the subsequent steps of our methodology. Table 1 shows the breakdown of failing coding tasks per LLM and benchmark. Note that we had to exclude one task from HumanEval+ and three tasks from MBPP+ since their tests were not providing error messages when failing, thus not allowing their usage in the optimization process, resulting in 163 coding tasks for HumanEval+ and 375 for MBPP+.

### 3.4 Code Optimization Process

We perform an iterative code optimization inspired by the approach by Pryzant et al. [45]. We utilize the LLMs to generate new code based on feedback derived from test failures, until the code passes the tests or a maximum number of optimization attempts have been made. The optimization process begins with the code generation prompt we described in Section 3.3, which is again provided to the LLMs to get the output code. Remember that this is done only for the coding tasks for which the same prompt provided to the same LLM already failed ten times in generating a correct implementation (as described in Section 3.3). Thus, we expect that the specific LLM would fail this time as well. Still, we assess the code against the corresponding test suite. If (surprisingly) the tests pass, the optimization process stops, and this instance is discarded (this never happened in our experimentation.) Otherwise, we provide the LLM the following code-optimization prompt: Code optimization prompt I’m trying to write a zero-shot prompt for code generation. This is the [round] round of optimization. My starting prompt is: "[prompt]" In the last round of optimization, you provided this code snippet: "[code]" But this source code does not pass the test cases, failing with the following messages: "[error]" Based on the above information, provide a new code snippet that satisfies the requirements and passes the test cases. The code-optimization prompt contains four tags: “round” indicates the 𝑖 𝑡ℎ iteration of the optimization process; “prompt”refers to

Table 1: Code generation results with ten runs per task: Number of tasks that passed at least once and always failed. The total number of tasks is 1,140 for BigCodeBench, 163 for HumanEval+, and 375 for MBPP+ Code Generation Results GPT-4o mini

Benchmark HumanEval+ MBPP+ BigCodeBench

#At least one pass

#Always fail

145 265 715

18 110 425

Llama 3.3 70B Instruct

Benchmark HumanEval+ MBPP+ BigCodeBench

#At least one pass

#Always fail

132 248 680

31 127 460

Qwen2.5 72B Instruct

Benchmark HumanEval+ MBPP+ BigCodeBench

#At least one pass

#Always fail

134 258 651

29 117 489

DeepSeek Coder V2 Instruct

Benchmark HumanEval+ MBPP+ BigCodeBench

#At least one pass

#Always fail

134 276 705

29 99 435

the starting code generation prompt; “code” is the code generated in the previous round of optimization (or the code produced from the initial prompt in the first round); and “error” contains the error messages from testing the previously generated code. The code outputted by the LLMs is again tested and, in case of failure, another round of code optimization is triggered. If the LLM is unable to generate a valid source code within five rounds, the process halts, and the coding task is discarded. In case of code-passing tests, instead, we store: (i) the original prompt used for the code generation; (ii) all test error messages collected during the code optimization rounds; (iii) the test-failing implementations seen during the process; and (iv) the test-passing code which stopped the process. This process is performed for each LLM independently, so it is possible that some tasks are discarded for one LLM but kept for another. A total of 229, 261, 268, and 228 instances were successfully optimized by GPT-4o mini, Llama 3.3, Qwen2.5, and DeepSeek, respectively, thus progressing to the next step of prompt optimization.

### 3.5 Prompt Optimization & Validation

At this point, we instruct each LLM to provide a new zero-shot prompt by learning from the information derived from the codeoptimization process. We prompt the LLMs as follows:

Guidelines to Prompt Large Language Models for Code Generation: An Empirical Characterization

Listing 1: Original prompt 1 2

def decimal_to_binary ( n ) : " " " Write ␣ a ␣ function ␣ to ␣ convert ␣ the ␣ given ␣ decimal ␣ number ␣ to ␣ its ␣ binary ␣ equivalent , ␣ represented ␣ as ␣ a ␣ string ␣ with ␣ no ␣ leading ␣ zeros . " " "

Listing 2: Optimized prompt 1 2

def decimal_to_binary ( n ) : " " " Convert ␣ a ␣ given ␣ decimal ␣ integer ␣ to ␣ its ␣ binary ␣ representation ␣ as ␣ a ␣ string . ␣ ␣ ␣ ␣ The ␣ function ␣ should ␣ handle ␣ both ␣ positive ␣ and ␣ negative ␣ integers , ␣ returning ␣ ␣ ␣ ␣ the ␣ binary ␣ equivalent ␣ without ␣ leading ␣ zeros . ␣ For ␣ negative ␣ integers , ␣ ␣ ␣ ␣ the ␣ binary ␣ representation ␣ should ␣ be ␣ prefixed ␣ with ␣ a ␣ '-'␣ sign . ␣ ␣ ␣ ␣ If ␣ the ␣ input ␣ is ␣ zero , ␣ return ␣ '0 '. " " "

Figure 2 illustrates a representative example of prompt refinement. The original prompt provides only a general task description, which leaves several ambiguities in the expected behavior of the generated code. In contrast, the optimized prompt explicitly specifies input/output formats and post-conditions, defining precise behavior for positive, negative, and zero inputs. These clarifications ensure that the returned value satisfies well-defined constraints, improving both predictability and correctness.

Figure 2: Original (top) and optimized (bottom) prompt. Example from the mbpp dataset, task id: 99, LLM used: GPT-4o

Figure 2: Original (top) and optimized (bottom) prompt. Example from the mbpp dataset, task id: 99, LLM used: GPT-4o mini Prompt optimization I’m trying to write a zero-shot prompt for code generation. This is the [round], and last, round of optimization. My starting prompt is: "[prompt]" In the previous steps of optimizations, the codes you provided did not pass the test cases, failing with the following messages: [error] In the last rounds of optimization, you provided this code snippet: "[code]" This code successfully passed all test cases. Based on the above information, provide a new prompt that, differing from the starting prompt, will provide enough details to generate a code snippet that passes the test cases. Wrap the new prompt between triple quotes. This prompt includes four customizable tags: “round” indicates the 𝑖 𝑡ℎ and last iteration of the optimization process; “prompt” is again the starting prompt used in the code generation process; “error” is a list of pairs <code, errors>, where each pair corresponds to a test-failing code generated during the code optimization process, reporting the generated code and the corresponding test failures. Finally, “code” is the test-passing code output of the code optimization process. This provides the LLMs with contextual information related to all previously generated code, offering a comprehensive view of the information missing in the original prompt. The fixed prompts 𝑃 𝑓 outputted by the LLMs, which should result in test-passing codes, are provided ten times as input to the LLMs to verify whether the resulting codes are actually correct. If any of those ten runs result in passing tests, we consider 𝑃 𝑓 as a successfully optimized prompt, and pair it with the original prompt 𝑃𝑜 (i.e., the one used in the very first code generation step — Section 3.3). Such pairs constitute the input for the subsequent manual inspection aimed at identifying prompt guidelines. In total, GPT-4o mini, Llama 3.3, Qwen2.5, and DeepSeek succeeded in creating an optimized prompt for 153, 192, 200, and 145 instances, respectively.

Identification of Guidelines

We manually inspect all instances for which LLMs were able to generate a test-passing prompt, starting from a test-failing one. We divided all optimized prompts into three groups, each assigned to two authors acting as inspectors. Within each group, the set of prompts was split between the two inspectors: each analyzed their own subset and a counter-analysis of the other inspector’s subset. This makes every classification double-checked. To perform the analysis, each inspector had access to: (1) A diff file (in HTML) highlighting the differences between each starting prompt and its optimized version. (2) The test log, reporting the failures that occurred during the iterative process. In total, 224/627 of the inspected instances resulted in a conflict (i.e., a different set of optimization guidelines defined by the two inspectors). Such a high number of conflicts is expected since we did not start from a pre-defined catalogue of guidelines, but we derived it as we moved on in the process. Afterwards, each pair of inspectors resolved the conflicts in their classifications through open discussion. To define the guidelines, the evaluators identified the elements of the prompt that were added, removed, or changed. At the same time, they examined whether the changes (i) included the implementation of the code itself, or (ii) incorporated too specific requirements which could only be known by reading the tests. We excluded the first category, as the inclusion of implemented code could introduce bias into the generation of new prompts during the optimization phase. We also excluded the second since those contained pieces of information not available in the original task specification, which a developer could only have access to in a test-driven development scenario. Once the manual analysis was completed, two authors scrutinized the list of all possible guidelines identified and consolidated it by merging very similar ones where appropriate. In the end, we obtained a set of 10 guidelines.

### 3.7 Guideline Evaluation

To evaluate the elicited guidelines, we conduct a study in which we ask practitioners the extent to which they (i) have used, in their code generation tasks, the prompt improvement strategies from our guidelines, as well as other optimizations we may have missed, and (ii) perceive each guideline as useful, regardless of their actual usage. The study participants have been recruited through the authors’ professional network. The study has been administered as a survey questionnaire (available in our replication package [7]) conducted using Google Forms. The questionnaire structure features three sections in which we collect:

Table 2: Guidelines proposed to improve prompts during code generation Guidelines

Guideline Requirements Pre-conditions Post-conditions I/O format Exceptions Algorithmic Details Variable Mentioning Unclear Conditions More Examples Assertive Language

Description Applied Make requirements explicit in terms of needed packages or libraries, and explain what to 19% use them for. Specify pre-conditions (e.g., a data structure provided as input must be non-empty). 7% Specify post-conditions (e.g., the return value is expected to be in a certain range). 23% Specify input/output and return format (if complex), and document special cases. 44% If exceptions must be raised or error messages must be printed, be specific in reporting 12% which exceptions to raise and how, or which error messages to write and where. Detail algorithmic aspects of the code, ensuring the correctness of complex features with 57% supporting notes if necessary, and include definitions or formulas for clarity and accuracy. Don’t use generic terms to refer to different variables or different terms to the same 3% variable. When specifying a condition, do not use “otherwise” referring to the second condition. 1% Instead, describe both conditions explicitly. Add some examples of run (i.e., doctests). 24% For required functionality, use non-ambiguous language, e.g., use “must” instead of “should”. 9% Use more assertive language.

(1) Background information: This includes study title, development experience in years, and experience with the use of LLMs in software development; (2) Usage of the studied prompt improvement strategies: we use a 5-level scale in which we ask the participants to estimate the frequency (i.e., % of code generation prompts they write) in which they use the considered guideline (Never, <25%, between 25% and 50%, between 50% and 75%, over 75% of the prompts). Also, we ask them to specify whether they use any other prompt improvement strategy that is not considered in our guidelines. (3) Perceived usefulness of the studied prompt improvement strategies: In this case, we ask—using a 5-level Likert scale [38] from “completely useless” to “very useful”—the perceived level of usefulness of each prompt improvement guideline, regardless of its usage. We kept the questionnaire open for three weeks. Out of about 70 invitations, we collected 50 valid responses. Questionnaire demongraphics. The study participants are pretty diversified in terms of expertise. This may reflect a diverse population of developers who may interact with LLMs to generate code. Nowadays, even quite inexperienced programmers do that. Most of the participants held an M.Sc. (19) or a B.Sc. (19), whereas 9 have a Ph.D. and 3 are students with a high school degree. The development experience is between 1 and 5 years (22) or between 5 and 10 (20), with 3 participants with over 10 years of experience and 5 with less than one year of experience. Most of them use ChatGPT (45), followed by GitHub Copilot (24), Gemini (14), Claude (10), DeepSeek (4), Perplexity (2), and JetBrains AI assistant (1). Participants report using LLMs in less than 25% of their development activities (11), 25-50% (22), 50-75% (8), and over 75% (9).

RESULTS DISCUSSION

In the following, we discuss results addressing the three RQs.

### 4.1 RQ1 : Identified Guidelines

Table 2 overviews the 10 guidelines we derived. The table indicates name, short description, and the percentage of instances (out of the 627 for which the LLMs were able to generate an optimized prompt) in which the LLMs applied such an optimization pattern. We detail the guidelines in the following. The “ID" allows for tracing the examples through our replication package [7]. Requirements. Explicitly state all requirements needed for the code to function correctly. It is also important to explain the purpose of each dependency (e.g., “use numpy for numerical array operations” rather than simply “import numpy”). This makes it more likely that the generated code includes correct imports and uses each dependency appropriately. Such a guideline has been applied in 19% of optimized prompts. A concrete example of prompt optimization made by the LLMs by adopting this guideline concerns an instance from the BigCodeBench benchmark (ID: 125), in which the original prompt only listed a set of requirements to be used (i.e., Requirements: collections.defaultdict) while the optimized one by GPT-4o mini explained the role played by each dependency (i.e., Use collections.defaultdict to count letter occurrences). Pre-conditions. Define conditions that must hold before execution. For example, specify that “the input list must be non-empty” or “the matrix must be square.” This helps avoid invalid assumptions and ensures robust error handling. Such a guideline, applied in 7% of optimized prompts, has been adopted by GPT-40 mini when implementing a function to backup a given source folder to the specified backup directory. The LLM added to the prompt “Ensure that the backup directory is writable and has sufficient space”, to avoid writing exceptions observed in previous, unsuccessful, implementations. Post-conditions. Specify a condition that shall be valid after code execution, e.g., guarantees about the produced outputs (e.g., “the function returns a sorted list in ascending order” or “the result

Guidelines to Prompt Large Language Models for Code Generation: An Empirical Characterization

must be within [0, 1]”). Explicit post-conditions help the model verify the correctness of its output logic. The LLMs applied such a guideline in 23% of the optimized propts. As an example, specifying a post-condition was needed for one of the MBPP+ tasks (ID 99), asking for the conversion of a decimal number into its binary format. The original prompt does not specify that "for negative integers, the binary representation should be prefixed with a ‘-’ sign". Such a sentence has been added by GPT-4o mini in the optimized prompt. Input/Output Format. Clarify input and output data types, shapes, and structures, including any special or edge cases. The application of such a guideline is crucial, especially when dealing with more complex I/O structures. This is the second-most applied guideline, with 44% of optimized prompts involved. For example, one of the always-failing coding tasks from BigCodeBench (ID 267) asked the LLM to plot specific information from a data dictionary. However, there were missing specifications about the expected format of such a plot. The following additions resulted in a test-passing code: The plot should have: - X-axis labeled as ‘Frequency [Hz]’; - Y-axis labeled as ‘Frequency Spectrum Magnitude’. Exceptions and Error Handling. If the code must handle errors or raise exceptions, describe these explicitly. Specify which exceptions to raise and under what conditions. If error messages must be printed, describe what message to print and where. Avoid vague wording like “handle the error gracefully”; instead, define explicit exception types and messages. The specification of possible errors could relate to several parts of the coding tasks to be accomplished, and has been employed in 12% of the optimized prompts. We observed GPT-4o mini optimizing the prompt (ID 560) from bigcodebench to include cases related to unexpected input parameters (e.g., This function plots a bar chart of monthly data values for a single year, with ‘month’ on the x-axis and ‘value’ on the y-axis. The function should raise a ValueError if the data contains entries from multiple years.), as well as to unrespected precoditions in bigcodebench (ID 150),e.g., Ensure that if a product key in product_keys does not exist in product_dict, a KeyError is raised.. In some cases, the exceptions to raise were already documented in the original prompt, but not all scenarios causing the raising of the exception were documented (e.g., GPT-4o mini added “or if the script file does not exist” to a sentence explaining cases in which a ValueError should be reported, bigcodebench, ID 460). This case shows how minor specifications in a prompt may make the difference between a test-passing and a test-failing implementation. Algorithmic details. Provide essential algorithmic details for complex logic. It is important to include supporting definitions, formulas, or theoretical notes where needed to ensure correctness. This helps the generated code follow the intended method rather than guessing or simplifying, and it is the most frequently applied prompt optimization guideline (57% of cases). In one prompt optimized using this guideline (MBPP+, ID 781), GPT-4o mini expanded the original prompt (i.e., Write a python function to check whether the count of divisors is even) by adding: The function should efficiently count divisors by iterating

only up to the square root of n. In another case, GPT-4o mini clarified the definition of Jacobsthal number, which was not present in the original prompt, by adding: The Jacobsthal numbers are defined as follows: J(0) = 0, J(1) = 1, and for n > 1, J(n) = J(n-1) + 2 * J(n-2) (MBPP+, ID 752). Variable mentioning. Maintain consistent terminology. Do not use generic or interchangeable terms for different variables. Use the same term consistently for the same variable throughout the prompt. This minimizes confusion and ensures variable names and references remain coherent. While only 3% of the optimized prompts benefited from such a guideline, it is interesting to see how simple linguistic variations helped code generation. In one of the original prompts of BigCodeBench (ID 731), the function to be generated takes as input two parameters named data and target. However, in the description of the code to implement, the original prompt refers to these two parameters as “data” (coherent with the parameter’s name) and “destination” (not coherent) — Save the Sklearn dataset ("Data" and "Destination") in the pickle file. GPT-4o mini revises this inconsistency by rephrasing the sentence as: Save the provided Sklearn dataset (data and target) into a pickle file. Clarity in conditions. Avoid ambiguous phrasing such as “otherwise” when describing conditional logic. Instead, specify both conditions explicitly (e.g., “If x > 0, do A; if x <= 0, do B”). This prevents the model from making incorrect assumptions about conditional relationships. Typical fixes of the LLMs included the replacement of the “otherwise” when describing the second condition of a selection construct, e.g., from BigCodeBench (ID 477) optimized by GPT-4o mini: [...] if N is greater than or equal to the number of categories, otherwise it is randomly sampled without replacement from CATEGORIES to: [...] if N is greater than or equal to the number of categories. If N is less than the number of categories, sample without replacement. We only found a few cases of such an optimization (1% of the instances). More examples. Provide concrete examples or doctests demonstrating expected behavior. Examples make the functionality clearer and serve as an informal test of correctness. The examples added by the LLMs in 24% of the optimized prompts often aim at documenting possible corner cases that must be handled. For example, in a function aimed at building a pandas DataFrame based on two lists provided as input, GPT-4o mini added the last three of the four usage examples shown below, with the first one already part of the original prompt, and task_func being the name of the function to implement (BigCodeBench, ID 553): task_func([1, 2, 3], [‘A’, ‘B’, ‘C’, ‘D’, ‘E’]) task_func([], []) task_func([1, 2, 3], []) task_func([], [‘A’, ‘B’, ‘C’]) Assertive Language. Use precise, assertive language to express requirements and constraints. Prefer “must” or “is required to” instead of “should” or “may.” This reduces uncertainty and may increase the chances that the generated code adheres strictly to the

Assertive Language

28%

24%

More Examples 4%

48%

Unclear Conditions

8%

Variable Mentioning

10%

Algorithmic Details

I/O format 2%

28%

Preconditions

6%

32%

10%

28%

22%

12%

24%

10%

22%

25%

50%

10% 20%

32%

42%

8%

22% 26%

2% 10%

22%

30% 26%

12%

22%

22% 8%

0%

20% 20%

38%

2% 8%

30%

26%

Postconditions

Requirements

30%

48%

8%

16%

10%

40%

16%

Exceptions

30%

16%

75%

10%

100%

Percentage of responses 0% (Never)

<25%

25−50%

50−75%

>75%

Figure 3: Prompt improvement patterns usage frequency specification. Such a guideline has been implemented by the LLMs in 9% of optimized prompts, by injecting assertive terms such as “ensure that”. RQ1 Summary We elicited 10 guidelines for code generation prompt optimization. These were related to aspects concerning key aspects of code behavior, such as I/O format, and pre/post conditions, but also detailed and technological aspects, such as requirements, unclear conditions, and exceptions, and, finally, textual ambiguities.

### 4.2 RQ2 : Improvement pattern usage by the study participants

When we asked participants how frequently they perform prompt improvements, they reported doing it in 25% of their prompts (11), 25-50% (21), 50-75% (12), and over 75% (6). Figure 3 shows a plot depicting the extent to which the study participants used the different prompt improvement patterns emerging from our guidelines. Results are reported with stacked bars with different color intensity representing the usage percentage of each prompt improvement pattern. In interpreting them, one should not expect a pattern to be used in the majority of the prompts, as it may only apply to specific scenarios. Requirements, i.e., library imports, have a relatively mild use. Only 10% report specifying them in over 75% of the prompts, 16% in 50-75%, and 22% in 25-50% of them. This may be since our respondents do not interact with LLMs having a specific technology

in mind, unless they are already using some and need to enforce it. Therefore, they expect the LLM to provide the requirements itself. Both pre-conditions and post-conditions are among the patterns with a relatively higher frequency of use, with the majority of respondents indicating that they use them at least in 25-50% of the prompts, even though the very frequent use (over 75% of the prompts) is limited to 10% of the respondents. This is expected when one wants to generate a non-trivial method/function and wants to check the inputs or the produced outputs. Even more used is the specification of the I/O format. Especially (and not only) for data processing functions, this allows an easier integration of the generated code with the rest of one’s own system, or in general, an easier usage of the function. Less used are patterns aimed at specifying exceptions. While the majority uses it in at least 25-50% of the prompts, only 10% do so in over 75% of them. This may depend either on the need to adapt exception handling to the rest of the system or on the fact that during code generation, handling exceptional cases is not the priority, except for specific functions. Similar results are observed for algorithmic details, which may apply only to functions whose behavior needs to be explicitly specified, and cannot be inferred from the general description. Improving prompts to maintain a consistent terminology for the used variables is done by only 10% of the participants on over 75% of the prompts, 12% in 50-75% of the prompts, and 20% in 25-50% of them. This is more of a linguistic optimization, which resulted from our analysis, yet respondents did not think about it in their activities. This may also be because the starting prompts used by participants feature explicit variable names, but more of the code logic.

Guidelines to Prompt Large Language Models for Code Generation: An Empirical Characterization

I/O format

4%

8%

88%

Preconditions

6%

16%

78%

More Examples

10%

16%

74%

Postconditions

8%

24%

68%

Assertive Language

16%

22%

62%

Requirements

24%

18%

58%

Algorithmic Details

24%

24%

52%

Exceptions

18%

36%

46%

Variable Mentioning

30%

28%

42%

Unclear Conditions

30%

28%

42%

100

50

50

100

Percentage Response

Totally Useless

Moderately Useless

Neutral

Moderately Useful

Very Useful

Figure 4: Perceived usefulness of the pattern improvement guidelines. Unclear conditions tend to be improved by the majority of respondents in at least 25-50% of the cases, although only 2% report doing so for over 75% of the prompts. Such needs for improvement are a circumstance that may occur only in specific code generation scenarios/functions where conditions are particularly complex or ambiguous. Surprisingly, specifying more examples was reported to be used in 25-50% of the cases by less than the majority of respondents (overall, 48% of them), with only 8% doing so in over 75% of the prompts. This may even depend, once again, on the specific development scenario, but also on the limited attitude in doing so and in leveraging examples when writing code, e.g., in a context of test-driven or behavior-driven development [25, 31, 36]. The least used pattern relates to using assertive language. This confirms, in a more general meaning, what found about variable mentioning, i.e., a limited use of linguistic-related improvements. Besides reporting usage frequencies for patterns related to our guidelines, we also asked participants to report other prompt improvement strategies not present in our guidelines. They reported the following: • More contextual information (seven responses), including signatures of other methods/functions in the system/file or information about other components. Clearly, this also depends on the tool being used, e.g., some LLM-based assistants such as GitHub Copilot are better capable of capturing context than Web-based ones; • Coding standards (two responses); • Testability requirements (one response); and • Non-functional aspects to optimize (one response).

RQ2 Summary Out of the 10 elicited prompt optimization patterns, the study participants admitted to mainly using those related to I/O and pre- and post-conditions. Improvements related to textual ambiguity were seldom adopted, and this was also the case for those aimed at driving code generation by providing I/O examples.

### 4.3 RQ3 : Perceived usefulness of the guidelines

Besides asking the study participants to report their usage of the prompt improvement patterns from our guidelines, we also asked them to evaluate their perceived usefulness. Results are reported in Figure 4. On the one side, the figure confirms, in terms of perceived usefulness, what the study participants have reported using. Indeed, explicitly specifying the I/O format is perceived as useful by almost all participants (88%), and high percentages are also reported for pre-conditions and post-conditions. Similarly, some very specific improvement patterns were considered relatively less useful, consistent with their limited usage. These include, for example, a lack of coherent variable mentioning, making the handling of exceptions explicit, or better specifying unclear conditions. For the last two cases, this confirms their applicability in a limited proportion of scenarios. On the other side, some guidelines whose patterns were reported to be rarely used were, instead, considered quite useful. Above all, this was the case of providing more examples. This is a confirmation of the fact that their limited usage may simply depend on a lack of awareness. We also observed a relatively high perception of usefulness, somewhat contrasting with the relatively lower usage, for better

specifying dependency requirements, as well as for clarifying ambiguities.

RQ3 Summary The study participants consistently perceived as useful some of the prompt improvement patterns they actually use, especially those related to pre- and post-conditions and I/O format. At the same time, they found useful guidelines related to driving the LLM by adding more I/O examples, but they also appreciated the need to avoid textual ambiguities.

## THREATS TO VALIDITY

Threats to construct validity concern the relationship between theory and observation, and may arise both in the prompt elicitation phase and in their validation. Regarding the elicitation, we avoided considering cases in which the LLMs tried to overfit test cases as an improvement pattern. Regarding the validation, our study does not measure the guideline usage effectiveness or efficacy, nor does it provide exact measures of actual usage. Instead, we leverage selfreported use admission, which could be imprecise. Similarly, the perceived usefulness is not intended to represent an actual usefulness measured during a development task, and therefore can be affected by the participants’ subjectivity. Threats to internal validity concern factors internal to our study that may affect our findings. As we explained in Section 3.2 during the automated code optimization, we used proper precautions to mitigate effects related to nondeterminism. We mitigated errors and subjectivity in our manual guideline elicitation by having two evaluators for each instance, who reviewed and resolved inconsistent cases. Note that agreement by chance may not influence the conclusions of our study, because in RQ1 we were merely interested in identifying possible improvement patterns, rather than in exactly assigning patterns to tasks. The patterns were then validated with the study reported in RQ2 and RQ3 . Regarding the guideline evaluation, we mitigated threats related to the questionnaire design by following proper survey design guidelines [23, 43] and by having authors not involved in its design to validate it. Concerning the study participants, while their demographics indicate a good diversity in experience and expertise, we cannot exclude a self-selection bias. Threats to external validity concern the generalizability of our findings. Concerning the prompt elicitation, two key elements may limit the generalizability of our findings. One is related to the choice of the three used benchmarks (BigCodeBench, HumanEval+, and MBPP+), and another to the specific programming language considered (Python). For the former, we have leveraged general-purpose and diverse benchmarks in terms of code tasks. However, we cannot exclude the possibility that leveraging other benchmarks may lead to further guidelines. Also, while our guidelines are totally language-agnostic, there could be improvement patterns that apply to some specific languages than others. These threats were mitigated through the validation with practitioners, by asking them whether we missed some improvement patterns.

Last but not least, our study participants may not represent a wide population of developers, especially very expert ones. However, they cover a wide range of experience and expertise that may represent well enough practitioners interacting with LLMs for code generation.

IMPLICATIONS

This section discusses implications deriving from our work that can affect different kinds of stakeholders. Concerning software development practitioners, the elicited guidelines can constitute a reference point to be followed when interacting with LLMs during code generation. While some optimizations (e.g., those related to I/O, pre- and post-conditions, examples, or checking for textual ambiguity) may apply in most cases, developers may adopt other guidelines in specific circumstances. For example, those related to requirements may be applied once the technology to be used is known, whereas those pertaining to exceptions can be part of the inputs to apply to achieve better code robustness (e.g., on the line of what related work did for code preferences [54]), but once again, when enough contextual details are known. In general, creating a decision tree explaining to developers which elements to improve in their prompts might be desirable, and when. What was said above also translates into implications for educators. Prompt engineering is nowadays becoming part of learning elements in curricula [10, 52]. To this extent, our guidelines can represent a key component to be used to instruct software engineers in doing prompt engineering for code generation. Tool creators and, in general, researchers working on creating novel recommenders for software development, could leverage our results to develop better tools. For example, tools could automatically analyze the prompt and the surrounding context, provide suggestions to the developers, and try to improve the prompt automatically if they realize that some needed elements are missing or unclear.

## CONCLUSIONS AND FUTURE WORK

In this paper, we have empirically defined a catalog of prompt optimization guidelines for LLM code generation. The guidelines have been defined by (i) iterating the interaction with the LLMs to make it pass tests and then asking it to optimize the prompt based on the successful iteration, and (ii) performing a manual analysis of the optimization differences between the initial and final prompts. We obtained 10 code-specific prompt optimization guidelines, covering different aspects, such as I/O formatting, preand post-conditions, I/O examples, dependencies, implementation aspects (algorithms, exceptions, complex conditions), and different forms of ambiguities. We have validated the guideline catalog through a study with 50 practitioners, investigating the extent to which they (i) already use the prompt optimization patterns in our guidelines, and (ii) perceive them to be useful. On the one hand, results of the study indicate that participants consider some of the elicited guidelines—such as those related to I/O formatting and pre-post conditions—as part of their prompt engineering activity, whereas those pertaining to ambiguities and I/O examples were less used. On the other hand,

Guidelines to Prompt Large Language Models for Code Generation: An Empirical Characterization

they perceived the latter particularly useful, along with those they already use. The study leads towards implications for different stakeholders, primarily developers and educators, who can leverage the guidelines to improve their code or to instruct new practitioners about code-specific prompt engineering, but also researchers and tool creators, as they could leverage the guidelines to craft tools for automated code generation, prompt guidance, and optimization. Work-in-progress goes towards different avenues. We would like to extend our empirical investigation to other languages and tasks. Also, we plan to conduct controlled experiments to assess the actual guidelines’ usefulness. Finally, as mentioned above, it would be worthwhile to leverage the guidelines to create tools for automated prompt quality assessment and improvement.

## DATA AVAILABILITY

The study dataset is available in our replication package [7].

## REFERENCES

[1] [n. d.]. DeepSeek-Coder-V2-Instruct-0724. https://www.huggingface.co/ deepseek-ai/DeepSeek-Coder-V2-Instruct-0724. Accessed: 2025-10-01. [2] [n. d.]. GPT-4o mini. https://platform.openai.com/docs/models/gpt-4o-mini. Accessed: 2025-10-01. [3] [n. d.]. Llama 3.3 70B Instruct. https://huggingface.co/meta-llama/Llama-3.370B-Instruct. Accessed: 2025-10-01. [4] [n. d.]. Qwen2.5 72B Instruct. https://huggingface.co/Qwen/Qwen2.5-72BInstruct. Accessed: 2025-10-01. [5] Seif Abukhalaf, Mohammad Hamdaqa, and Foutse Khomh. 2024. PathOCL: PathBased Prompt Augmentation for OCL Generation with GPT-4. In Proceedings of the 2024 IEEE/ACM First International Conference on AI Foundation Models and Software Engineering (Lisbon, Portugal) (FORGE ’24). 108–118. https://doi.org/ 10.1145/3650105.3652290 [6] Toufique Ahmed, Kunal Suresh Pai, Premkumar Devanbu, and Earl Barr. 2024. Automatic Semantic Augmentation of Language Model Prompts (for Code Summarization). In Proceedings of the IEEE/ACM 46th International Conference on Software Engineering (Lisbon, Portugal) (ICSE ’24). Article 220, 13 pages. https://doi.org/10.1145/3597503.3639183 [7] Anonymous. [n. d.]. Replication Package of the paper "Guidelines to Prompt Large Language Models for Code Generation: An Empirical Characterization". https://doi.org/10.5281/zenodo.17431603. Accessed: 2025-10-20. [8] Chetan Arora, Ahnaf Ibn Sayeed, Sherlock Licorish, Fanyu Wang, and Christoph Treude. 2024. Optimizing Large Language Model Hyperparameters for Code Generation. arXiv:2408.10577 [cs.SE] 10.48550/arXiv.2408.10577 [9] Jacob Austin, Augustus Odena, Maxwell Nye, Maarten Bosma, Henryk Michalewski, David Dohan, Ellen Jiang, Carrie Cai, Michael Terry, Quoc Le, et al. 2021. Program synthesis with large language models. CoRR abs/2108.07732 (2021). https://doi.org/10.48550/arXiv.2108.07732 [10] Luciano Baresi, Andrea De Lucia, Antinisca Di Marco, Massimiliano Di Penta, Davide Di Ruscio, Leonardo Mariani, Daniela Micucci, Fabio Palomba, Maria Teresa Rossi, and Fiorella Zampetti. 2025. Students’ Perception of ChatGPT in Software Engineering: Lessons Learned from Five Courses. In 2025 IEEE/ACM 37th International Conference on Software Engineering Education and Training (CSEE&T). 158–169. https://doi.org/10.1109/CSEET66350.2025.00023 [11] Liguo Chen, Qi Guo, Hongrui Jia, Zhengran Zeng, Xin Wang, Yijiang Xu, Jian Wu, Yidong Wang, Qing Gao, Jindong Wang, et al. 2024. A survey on evaluating large language models in code generation tasks. arXiv preprint arXiv:2408.16498 (2024). [12] Mark Chen, Jerry Tworek, Heewoo Jun, Qiming Yuan, Henrique Ponde de Oliveira Pinto, Jared Kaplan, Harrison Edwards, Yuri Burda, Nicholas Joseph, Greg Brockman, Alex Ray, Raul Puri, Gretchen Krueger, Michael Petrov, Heidy Khlaaf, Girish Sastry, Pamela Mishkin, Brooke Chan, Scott Gray, Nick Ryder, Mikhail Pavlov, Alethea Power, Lukasz Kaiser, Mohammad Bavarian, Clemens Winter, Philippe Tillet, Felipe Petroski Such, Dave Cummings, Matthias Plappert, Fotios Chantzis, Elizabeth Barnes, Ariel Herbert-Voss, William Hebgen Guss, Alex Nichol, Alex Paino, Nikolas Tezak, Jie Tang, Igor Babuschkin, Suchir Balaji, Shantanu Jain, William Saunders, Christopher Hesse, Andrew N. Carr, Jan Leike, Joshua Achiam, Vedant Misra, Evan Morikawa, Alec Radford, Matthew Knight, Miles Brundage, Mira Murati, Katie Mayer, Peter Welinder, Bob McGrew, Dario Amodei, Sam McCandlish, Ilya Sutskever, and Wojciech Zaremba. 2021. Evaluating Large Language Models Trained on Code. CoRR abs/2107.03374 (2021). https://doi.org/10.48550/arXiv.2107.03374

[13] Zheng Chu, Jingchang Chen, Qianglong Chen, Weijiang Yu, Tao He, Haotian Wang, Weihua Peng, Ming Liu, Bing Qin, and Ting Liu. 2024. Navigate through Enigmatic Labyrinth A Survey of Chain of Thought Reasoning: Advances, Frontiers and Future. In Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers), Lun-Wei Ku, Andre Martins, and Vivek Srikumar (Eds.). Association for Computational Linguistics, Bangkok, Thailand, 1173–1203. https://doi.org/10.18653/v1/2024.acl-long.65 [14] Jean-Baptiste Döderlein, Mathieu Acher, Djamel Eddine Khelladi, and Benoit Combemale. 2022. Piloting copilot and codex: Hot temperature, cold prompts, or black magic? arXiv preprint arXiv:2210.14699 (2022). [15] Yihong Dong, Xue Jiang, Zhi Jin, and Ge Li. 2024. Self-Collaboration Code Generation via ChatGPT. ACM Trans. Softw. Eng. Methodol. 33, 7, Article 189 (Sept. 2024), 38 pages. https://doi.org/10.1145/3672459 [16] Xueying Du, Mingwei Liu, Kaixin Wang, Hanlin Wang, Junwei Liu, Yixuan Chen, Jiayi Feng, Chaofeng Sha, Xin Peng, and Yiling Lou. 2024. Evaluating Large Language Models in Class-Level Code Generation. In Proceedings of the IEEE/ACM 46th International Conference on Software Engineering (Lisbon, Portugal) (ICSE ’24). Association for Computing Machinery, New York, NY, USA, Article 81, 13 pages. https://doi.org/10.1145/3597503.3639219 [17] Ramtin Ehsani, Esteban Parra, Sonia Haiduc, and Preetha Chatterjee. 2025. Bug Fixing with Broader Context: Enhancing LLM-Based Program Repair via Layered Knowledge Injection. arXiv preprint arXiv:2506.24015 (2025). [18] Terry Yue Zhuo et al. 2024. BigCodeBench: Benchmarking Code Generation with Diverse Function Calls and Complex Instructions. https://doi.org/10.48550/ arXiv.2406.15877 arXiv:2406.15877 [cs.SE] [19] Ionut Daniel Fagadau, Leonardo Mariani, Daniela Micucci, and Oliviero Riganelli. 2024. Analyzing Prompt Influence on Automated Method Generation: An Empirical Study with Copilot. In Proceedings of the 32nd IEEE/ACM International Conference on Program Comprehension (Lisbon, Portugal) (ICPC ’24). 24–34. https://doi.org/10.1145/3643916.3644409 [20] Sarah Fakhoury, Aaditya Naik, Georgios Sakkas, Saikat Chakraborty, and Shuvendu K Lahiri. 2024. Llm-based test-driven interactive code generation: User study and empirical evaluation. IEEE Transactions on Software Engineering (2024). [21] Lishui Fan, Mouxiang Chen, and Zhongxin Liu. 2025. SEK: Self-Explained Keywords Empower Large Language Models for Code Generation. In Findings of the Association for Computational Linguistics: ACL 2025. 6249–6278. [22] Alexander Golubev, Maria Trofimova, Sergei Polezhaev, Ibragim Badertdinov, Maksim Nekrashevich, Anton Shevtsov, Simon Karasik, Sergey Abramov, Andrei Andriushchenko, Filipp Fisin, et al. 2025. Training long-context, multiturn software engineering agents with reinforcement learning. arXiv preprint arXiv:2508.03501 (2025). [23] Robert M. Groves, Floyd J. Jr. Fowler, Mick P. Couper, James M. Lepkowski, Eleanor Singer, and Roger Tourangeau. 2009. Survey Methodology (2nd ed.). Wiley, Hoboken, NJ. [24] Juyong Jiang, Fan Wang, Jiasi Shen, Sungju Kim, and Sunghun Kim. 2025. A Survey on Large Language Models for Code Generation. ACM Trans. Softw. Eng. Methodol. (July 2025). https://doi.org/10.1145/3747588 [25] Shanthi Karpurapu, Sravanthy Myneni, Unnati Nettur, Likhit Sagar Gajja, Dave Burke, Tom Stiehm, and Jeffery Payne. 2024. Comprehensive Evaluation and Insights Into the Use of Large Language Models in the Automation of BehaviorDriven Development Acceptance Test Formulation. IEEE Access 12 (2024), 58715– 58721. https://doi.org/10.1109/ACCESS.2024.3391815 [26] Ranim Khojah, Francisco Gomes de Oliveira Neto, Mazen Mohamad, and Philipp Leitner. 2025. The Impact of Prompt Programming on Function-Level Code Generation. IEEE Transactions on Software Engineering 51, 8 (2025), 2381–2395. [27] Jae Yong Lee, Sungmin Kang, and Shin Yoo. 2025. Predictive Prompt Analysis. https://doi.org/10.48550/arXiv.2501.18883 arXiv:2501.18883 [cs.SE] [28] Jinyang Li, Sangwon Hyun, and M. Ali Babar. 2025. DDPT: Diffusion-Driven Prompt Tuning for Large Language Model Code Generation. In 2025 IEEE/ACM 4th International Conference on AI Engineering – Software Engineering for AI (CAIN). 190–200. https://doi.org/10.1109/CAIN66642.2025.00030 [29] Jia Li, Yunfei Zhao, Yongmin Li, Ge Li, and Zhi Jin. 2024. AceCoder: An Effective Prompting Technique Specialized in Code Generation. ACM Trans. Softw. Eng. Methodol. 33, 8, Article 204 (Nov. 2024). [30] Jenny T. Liang, Melissa Lin, Nikitha Rao, and Brad A. Myers. 2025. Prompts Are Programs Too! Understanding How Developers Build Software Containing Prompts. Proc. ACM Softw. Eng. 2, FSE, Article FSE072 (June 2025), 24 pages. https://doi.org/10.1145/3729342 [31] Yunhao Liang, Chengguang Gan, Ruixuan Ying, and Zhe Cui. 2025. Exploring Behavior-Driven Development for Code Generation. In Advanced Intelligent Computing Technology and Applications: 21st International Conference, ICIC 2025, Ningbo, China, July 26–29, 2025, Proceedings, Part XXIII (Ningbo, China). SpringerVerlag, Berlin, Heidelberg, 41–51. https://doi.org/10.1007/978-981-95-0014-7_4 [32] Xiaoqiang Lin, Zhongxiang Dai, Arun Verma, See-Kiong Ng, Patrick Jaillet, and Bryan Kian Hsiang Low. 2024. Prompt Optimization with Human Feedback. https://doi.org/10.48550/arXiv.2405.17346 arXiv:2405.17346 [cs.LG] [33] Chao Liu, Xuanlin Bao, Hongyu Zhang, Neng Zhang, Haibo Hu, Xiaohong Zhang, and Meng Yan. 2023. Improving ChatGPT Prompt for Code Generation.

https://doi.org/10.48550/arXiv.2305.08360 arXiv:2305.08360 [cs.SE] [34] Jiawei Liu, Chunqiu Steven Xia, Yuyao Wang, and Lingming Zhang. 2023. Is your code generated by ChatGPT really correct? rigorous evaluation of large language models for code generation. In Proceedings of the 37th International Conference on Neural Information Processing Systems (New Orleans, LA, USA) (NIPS ’23). Curran Associates Inc., Red Hook, NY, USA, Article 943, 15 pages. [35] Yuetian Mao, Junjie He, and Chunyang Chen. 2025. From Prompts to Templates: A Systematic Prompt Template Analysis for Real-world LLMapps. https://doi. org/10.48550/arXiv.2504.02052 arXiv:2504.02052 [cs.SE] [36] Noble Saji Mathews and Meiyappan Nagappan. 2024. Test-Driven Development and LLM-based Code Generation. In Proceedings of the 39th IEEE/ACM International Conference on Automated Software Engineering (Sacramento, CA, USA) (ASE ’24). Association for Computing Machinery, New York, NY, USA, 1583–1594. https://doi.org/10.1145/3691620.3695527 [37] OpenAI. 2025. OpenAI Platform – Playground Prompts. https://platform.openai. com/docs/guides/prompt-engineering. Accessed: 2025-10-23. [38] A. N. Oppenheim. 1992. Questionnaire Design, Interviewing and Attitude Measurement. Continuum, London. Includes discussion of Likert scales and attitude measurement techniques. [39] Daniel Otten, Trevor Stalnaker, Nathan Wintersgill, Oscar Chaparro, and Denys Poshyvanyk. 2025. Prompting in Practice: Investigating Software Developers’ Use of Generative AI Tools. arXiv:2510.06000 [cs.SE] https://arxiv.org/abs/2510.06000 [40] Shuyin Ouyang, Jie M. Zhang, Mark Harman, and Meng Wang. 2025. An Empirical Study of the Non-Determinism of ChatGPT in Code Generation. ACM Trans. Softw. Eng. Methodol. 34, 2, Article 42 (Jan. 2025), 28 pages. https: //doi.org/10.1145/3697010 [41] Chao Peng, Qinyun Wu, Jiangchao Liu, Jierui Liu, Bo Jiang, Mengqian Xu, Yinghao Wang, Xia Liu, and Ping Yang. 2024. RepoSim: Evaluating Prompt Strategies for Code Completion via User Behavior Simulation. In Proceedings of the 39th IEEE/ACM International Conference on Automated Software Engineering (Sacramento, CA, USA) (ASE ’24). 2279–2283. https://doi.org/10.1145/3691620.3695299 [42] Yun Peng, Shuzheng Gao, Cuiyun Gao, Yintong Huo, and Michael Lyu. 2024. Domain Knowledge Matters: Improving Prompts with Fix Templates for Repairing Python Type Errors. In Proceedings of the IEEE/ACM 46th International Conference on Software Engineering (Lisbon, Portugal) (ICSE ’24). Article 4, 13 pages. https://doi.org/10.1145/3597503.3608132 [43] Shari Lawrence Pfleeger and Barbara A. Kitchenham. 2001. Principles of Survey Research: Part 1: Turning Lemons into Lemonade. ACM SIGSOFT Software Engineering Notes 26, 6 (2001), 16–18. https://doi.org/10.1145/505532.505535 [44] Kaiser Pister, Dhruba Jyoti Paul, Ishan Joshi, and Patrick Brophy. 2024. PromptSet: A Programmer’s Prompting Dataset. In Proceedings of the 1st International Workshop on Large Language Models for Code (Lisbon, Portugal) (LLM4Code ’24). 62–69. https://doi.org/10.1145/3643795.3648395 [45] Reid Pryzant, Dan Iter, Jerry Li, Yin Lee, Chenguang Zhu, and Michael Zeng. 2023. Automatic Prompt Optimization with “Gradient Descent” and Beam Search. In Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing, Houda Bouamor, Juan Pino, and Kalika Bali (Eds.). Association for Computational Linguistics, Singapore, 7957–7968. https://doi.org/10.18653/v1/ 2023.emnlp-main.494 [46] Kiran Ramnath, Kang Zhou, Sheng Guan, Soumya Smruti Mishra, Xuan Qi, Zhengyuan Shen, Shuai Wang, Sangmin Woo, Sullam Jeoung, Yawei Wang, Haozhu Wang, Han Ding, Yuzhe Lu, Zhichao Xu, Yun Zhou, Balasubramaniam Srinivasan, Qiaojing Yan, Yueyan Chen, Haibo Ding, Panpan Xu, and Lin Lee

Cheong. 2025. A Systematic Survey of Automatic Prompt Optimization Techniques. https://doi.org/10.48550/arXiv.2502.16923 arXiv:2502.16923 [cs.CL] [47] Jiho Shin, Clark Tang, Tahmineh Mohati, Maleknaz Nayebi, Song Wang, and Hadi Hemmati. 2025. Prompt Engineering or Fine-Tuning: An Empirical Assessment of LLMs for Code. In 2025 IEEE/ACM 22nd International Conference on Mining Software Repositories (MSR). 490–502. https://doi.org/10.1109/MSR66628.2025. 00082 [48] Mahan Tafreshipour, Aaron Imani, Eric Huang, Eduardo Santana de Almeida, Thomas Zimmermann, and Iftekhar Ahmed. 2025. Prompting in the Wild: An Empirical Study of Prompt Evolution in Software Repositories. In 2025 IEEE/ACM 22nd International Conference on Mining Software Repositories (MSR). 686–698. https://doi.org/10.1109/MSR66628.2025.00106 [49] Rosalia Tufano, Antonio Mastropaolo, Federica Pepe, Ozren Dabic, Massimiliano Di Penta, and Gabriele Bavota. 2024. Unveiling ChatGPT’s Usage in Open Source Projects: A Mining-based Study. In 21st IEEE/ACM International Conference on Mining Software Repositories, MSR 2024, Diomidis Spinellis, Alberto Bacchelli, and Eleni Constantinou (Eds.). ACM, 571–583. [50] Andreas Vogelsang, Alexander Korn, Giovanna Broccia, Alessio Ferrari, Jannik Fischbach, and Chetan Arora. 2025. On the Impact of Requirements Smells in Prompts: The Case of Automated Traceability. https://doi.org/10.48550/arXiv. 2501.04810 arXiv:2501.04810 [cs.SE] [51] Xinyuan Wang, Chenxi Li, Zhen Wang, Fan Bai, Haotian Luo, Jiayou Zhang, Nebojsa Jojic, Eric P. Xing, and Zhiting Hu. 2023. PromptAgent: Strategic Planning with Language Models Enables Expert-level Prompt Optimization. https://doi.org/10.48550/arXiv.2310.16427 arXiv:2310.16427 [cs.CL] [52] Jason L Weber, Barbara Martinez Neda, Kitana Carbajal Juarez, Jennifer Wong–Ma, Sergio Gago–Masague, and Hadar Ziv. 2024. Beyond the Hype: Perceptions and Realities of Using Large Language Models in Computer Science Education at an R1 University. In 2024 IEEE Global Engineering Education Conference (EDUCON). 01–08. https://doi.org/10.1109/EDUCON60312.2024.10578596 [53] Yuxin Wen, Neel Jain, John Kirchenbauer, Micah Goldblum, Jonas Geiping, and Tom Goldstein. 2023. Hard Prompts Made Easy: Gradient-Based Discrete Optimization for Prompt Tuning and Discovery. In Advances in Neural Information Processing Systems, A. Oh, T. Naumann, A. Globerson, K. Saenko, M. Hardt, and S. Levine (Eds.), Vol. 36. Curran Associates, Inc., 51008–51025. https://proceedings.neurips.cc/paper_files/paper/2023/file/ a00548031e4647b13042c97c922fadf1-Paper-Conference.pdf [54] Martin Weyssow, Aton Kamanda, Xin Zhou, and Houari Sahraoui. 2025. CodeUltraFeedback: An LLM-as-a-Judge Dataset for Aligning Large Language Models to Coding Preferences. ACM Trans. Softw. Eng. Methodol. (May 2025). https://doi.org/10.1145/3736407 Just Accepted. [55] Liangxuan Wu, Yanjie Zhao, Xinyi Hou, Tianming Liu, and Haoyu Wang. 2024. ChatGPT Chats Decoded: Uncovering Prompt Patterns for Superior Solutions in Software Development Lifecycle. In Proceedings of the 21st International Conference on Mining Software Repositories (Lisbon, Portugal) (MSR ’24). 142–146. https://doi.org/10.1145/3643991.3645069 [56] Dylan Zhang, Justin Wang, and Tianran Sun. 2025. Building A Proof-Oriented Programmer That Is 64% Better Than GPT-4o Under Data Scarcity. In Findings of the Association for Computational Linguistics: ACL 2025. 23101–23118. [57] Tanghaoran Zhang, Yue Yu, Xinjun Mao, Shangwen Wang, Kang Yang, Yao Lu, Zhang Zhang, and Yuxin Zhao. 2024. Instruct or Interact? Exploring and Eliciting LLMs’ Capability in Code Snippet Adaptation Through Prompt Engineering. https://doi.org/10.48550/arXiv.2411.15501 arXiv:2411.15501 [cs.SE]
