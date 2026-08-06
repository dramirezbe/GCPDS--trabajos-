
# Prompting in Practice: Investigating Software Practitioners' Use of Generative AI Tools

Daniel Otten, Trevor Stalnaker, Nathan Wintersgill, Oscar Chaparro, Denys Poshyvanyk
{dsotten, twstalnaker, njwintersgill, oscarch, dposhyvanyk}@wm.edu
William & Mary, Williamsburg, VA

## Abstract

The use of generative AI (GenAI) tools has fundamentally transformed software development. Central to this shift is prompt engineering, the practice of crafting textual prompts to guide GenAI tools in generating useful content. Although prompt engineering has emerged as a critical skill, prior research has focused primarily on cataloging of prompting techniques, with limited attention to how software practitioners employ GenAI within real-world development workflows. To address this gap, this study presents a systematic investigation of practitioners' integration of GenAI tools into software development, drawing on a rigorous survey that examines prompting strategies, conversation patterns, and reliability assessments across core software development tasks. We surveyed 72 software practitioners who actively use GenAI to characterize AI usage patterns throughout the development process. By combining qualitative and quantitative analyses of the survey responses, we identified 13 key findings that describe how prompting is performed in practice. Our study shows that while code generation is nearly universal, proficiency strongly correlates with the use of GenAI for more nuanced tasks such as debugging and code review. Practitioners also tend to favor iterative multi-turn conversations to single-shot prompting. Documentation tasks are perceived as most reliable, while complex code generation and debugging remain major challenges. Our findings provide an empirical view of practitioner practices, ranging from basic code generation to deeper integration of GenAI into development workflows, enabling us to offer recommendations for improving both GenAI tools and the ways practitioners interact with them.

## 1. Introduction

Software developers can now easily and quickly generate new code, review and modify existing codebases, identify and correct defects, and produce code documentation. Central to these capabilities is prompting: the practice of crafting natural language instructions to guide GenAI systems toward producing useful and accurate output. Prompting has emerged as a novel engineering practice, fundamentally different from traditional software development due to its reliance on large language models (LLMs), which are inherently probabilistic and non-deterministic, but highly capable [6]. Previous research has primarily focused on cataloging prompting techniques [41, 42, 51], which offers limited information on how practitioners actually use prompting in practice: how they craft prompts for different types of software engineering (SE) tasks, how they adapt to unreliable or suboptimal output, and how GenAI is reshaping standard development activities. Previous studies have examined narrow use cases (e.g., refactoring [2]), specific populations (e.g., students [3, 9]) and broader socio-organizational adoption factors [28, 40]. However, there remains a lack of systematic investigation into real-world prompting practices for a variety of SE tasks, which is essential to evaluate current practices, inform practitioners and educational guidance, and drive the design of more effective GenAI technology. To address this gap, we conducted a survey of 72 software practitioners, exploring how they use GenAI tools and engage in prompting across six core SE tasks: code generation, documentation, debugging, testing, refactoring, and review. (We use software practitioners to denote professionals with experience in programming and software development, including developers, architects, technical leads, researchers, and other roles.) Our study investigates multiple dimensions of GenAI usage, including the prompting and conversational strategies that practitioners employ, how they assess reliability, and the common issues they encounter.

GenAI, and for educators developing curricula around the evolving skill set needed for effective GenAI collaboration. This paper makes the following contributions: (1) a comprehensive characterization of how GenAI tools are used in various SE tasks; (2) empirical insights into practitioners' prompting strategies, reliability perceptions, and common failure types; and (3) actionable implications for improving human-AI interaction in SE.

## 2. Study Methodology

The goal of our study is to investigate how software practitioners use prompt engineering and GenAI tools for development tasks and what challenges they face during this use. The context consists of software practitioners with experience using GenAI tools for SE. Our study addresses the following research questions (RQs):

- RQ 1: How do software practitioners integrate GenAI tools into their development workflows?
- RQ 2: What prompting techniques and conversation strategies do practitioners use when interacting with GenAI tools?
- RQ 3: How reliable do practitioners perceive GenAI to be for various SE tasks and what are common issues they encounter?

Next, we detail our methodology (Figure 1), which aligns with our previous studies [45, 46, 52, 55] and was approved by our institution's ethics review board, including questionnaire, participant identification procedure, and data collection/distribution.

Figure 1: Study Methodology (image credits at [36])

### 2.1 Survey Design

We designed our survey questionnaire considering the existing literature on prompt engineering and the use of GenAI tools [42, 51], following general guidelines [18] and SE-specific guidelines for survey design [21–25, 31, 34, 37]. Through the survey, our goal was to build an understanding of GenAI integration across six core SE tasks: code generation, refactoring, testing, debugging, documentation, and code review. We selected these tasks because they span diverse development activities, are commonly supported by GenAI tools, and vary in complexity and risk, allowing a broad examination of prompting practices. This selection also balances task coverage with survey length, as we included task-specific questions. We implemented branching logic in the survey, so that participants were only shown questions relevant to their experiences (e.g., SE tasks for which they have used GenAI). To ensure data quality, we also included an initial question to screen out respondents with no experience using prompt-based GenAI tools. We carefully formulated the survey questions, ensuring that they were written clearly to avoid confusing or biasing the respondents. We also conducted a pilot study with graduate students from our research lab who regularly use GenAI tools. Based on their feedback, we further refined our questionnaire, improving questions that were unclear or confusing. The survey was organized into five sections. Sec. 1 collected demographic information. Sec. 2 asked questions related to the GenAI experience of the participants, the GenAI tools they regularly use, and their GenAI development workflows. Sec. 3 and 4 investigated the use of prompting techniques and conversation strategies. The final section explored the perceived reliability of GenAI tools and the issues that practitioners face. The questions were presented in a variety of formats, including multiple-selection, Likert scales, and open text fields. The full text and logic of our survey can be found in our replication package [36].

### 2.2 Participant Recruitment

Our recruitment strategy targeted software professionals with diverse backgrounds, including developers, architects, technical leads, researchers, and other roles with programming and software development experience. For survey distribution, we mainly relied on our professional networks and snowball sampling (e.g., participants sharing the survey within their networks) by directly contacting potential participants or posting participation calls on social media platforms (e.g., LinkedIn and X). To further broaden our sample and include professionals in earlier career stages, we distributed the survey to relevant organizations at our university, including the ACM chapter. Participants were not compensated monetarily or otherwise.

### 2.3 Data Collection and Analysis

Survey responses were collected using Qualtrics [1] between 27 May and 7 July 2025. To analyze the data, we used a mixed method approach, combining quantitative and qualitative techniques. For multiple choice and Likert scale questions, we calculated data distributions and descriptive statistics to identify trends and patterns. Where appropriate, to facilitate comparison, we assigned ordinal Likert scale responses (e.g., "Often" to "Never") to integer values (e.g., 1 to 4). This allowed us to compute mean scores to represent concepts such as the popularity of a prompting strategy or the frequency of an issue using GenAI tools. The responses to open-ended responses were analyzed using a qualitative coding approach [44]. Three annotators (i.e., authors) independently analyzed such responses and performed open-coding by assigning one or more codes to each response using a shared codebook (i.e., a spreadsheet). After the initial coding phase, the annotators met to collaboratively review, discuss, and reconcile the coding decisions. Through this process, the annotators developed a set of codes for each response, which are found in our replication package [36]. Since codes were developed iteratively through an inductive process without an initial codebook and multiple codes could be assigned to each response, we did not base our analysis on inter-annotator agreements. We followed best open-coding practices [44] and used annotator discussions to ensure the reliability of the results.

### 2.4 Participant Demographics

Our survey attracted 91 respondents who completed the survey, of whom 72 (79%) indicated having experience with GenAI tools and prompting. We answer our RQs based on these 72 responses. The 72 participants represent a diverse, global sample of software professionals, with reported development experience of 1-40 years (mean = 10.2, median = 10). They held a variety of roles, including researcher (64%), programmer (60%), technical lead (28%), and software architect (28%). Respondents could select multiple roles, and overlaps were common: for example, 31 of 46 participants identified as researchers (the most frequently selected role) also reported other roles, notably programmer, architect, technical lead, and/or tester. For comparative analysis, we grouped professional experience into four categories: 24 juniors (1–5 years), 22 intermediates (6–10 years), 19 seniors (11–20 years), and 7 veterans (21+ years). Participants reported having developed software across 43 distinct domains, with the most common being Healthcare (22%), Research (17.6%), Banking (15.4%), Software Development (12.4%), and Communication (10.1%). When asked to choose from a predefined list of eight system types, they most frequently indicated experience with web applications (63.9%), desktop applications (33.3%), libraries/frameworks (31.2%), and AI-intensive systems (30.6%). Respondents were located in 16 countries, with the majority residing in the United States (54%), followed by Canada (11%) and the United Kingdom (8%). The most commonly used programming languages were Python (63.9%), JavaScript (44.4%), Java (38.9%), C/C++ (27.8%), and TypeScript (25.0%).

## 3. Results

### 3.1 GenAI Usage and Workflow Integration

#### 3.1.1 GenAI Usage Across SE Tasks.

Reported. In general, 89% of the respondents reported using GenAI for four or fewer tasks, with two (30.6%) or three (23.6%) tasks being most common, suggesting a relatively focused use of GenAI. When analyzing the 5-Likert point responses of self-reported proficiency in using GenAI, we found that the majority of participants (57 of 72) considered themselves proficient or very/maximally proficient (see Table 1). (Since a single veteran practitioner rated themselves as having "minimum proficiency", we exclude this data point from future comparisons across proficiency levels.) We also observed that proficiency correlates with the number of SE tasks for which participants use GenAI (Spearman's ρ = 0.325). Among those who reported using GenAI for four or more SE tasks, most (18 of 22, 82%) identified as very or maximally proficient. By contrast, single-task users reported being somewhat proficient or proficient (7 of 11, 64%). These results suggest that task breadth and GenAI proficiency may mutually reinforce one another. When examining proficiency by software development experience, we found that junior and intermediate practitioners considered themselves more proficient in using GenAI that seniors and veterans. Specifically, 22 of 24 juniors and 19 of 22 intermediates reported being proficient or very/maximally proficient, compared to only 12 of 19 seniors and 4 of 7 veterans.

**Finding 1:** A moderate correlation between perceived GenAI proficiency and GenAI use across six SE tasks suggests that greater proficiency is associated with broader usage, and vice versa. Junior and intermediate practitioners tend to rate themselves as more proficient in using GenAI compared to senior and veteran practitioners.

#### 3.1.2 GenAI Usage Frequency and Tool Adoption.

Over 70% of respondents reported engaging with GenAI tools once or multiple times per day. Daily usage increases with proficiency: 35.7% of somewhat proficient users (5) reported daily GenAI use, as did 78.1% of proficient users (25), 83.3% of very proficient users (15), and 100% of maximally proficient users (7).

**Table 1: Proportion of respondents in each self-reported proficiency level who indicated GenAI use for each SE task.**

| GenAI Proficiency | Code Gen. | Refactoring | Testing | Debugging | Documentation | Code Review | Avg. # of tasks |
|---|---|---|---|---|---|---|---|
| Minimum Proficiency | 1/1 (100%) | 0/1 (0%) | 0/1 (0%) | 0/1 (0%) | 0/1 (0%) | 0/1 (0%) | 1.00 |
| Somewhat Proficient | 11/14 (78.5%) | 3/14 (21.4%) | 6/14 (42.9%) | 4/14 (30.8%) | 4/14 (30.8%) | 3/14 (23.1%) | 2.21 |
| Proficient | 32/32 (100%) | 11/32 (34.4%) | 9/32 (28.1%) | 16/32 (50%) | 14/32 (43.8%) | 8/32 (25.0%) | 2.81 |
| Very Proficient | 15/18 (83.3%) | 6/18 (33.3%) | 8/18 (41.2%) | 8/18 (41.2%) | 11/18 (58.8%) | 8/18 (41.2%) | 3.11 |
| Maximally Proficient | 7/7 (100%) | 3/7 (42.9%) | 5/7 (71.4%) | 4/7 (57.1%) | 5/7 (71.4%) | 4/7 (57.1%) | 4.00 |
| Total | 66/72 (91.7%) | 23/72 (31.9%) | 28/72 (38.9%) | 32/72 (44.4%) | 34/72 (47.2%) | 23/72 (31.9%) | 2.86 |

> *Figure 2: Productivity and task breadth by usage frequency*

**Finding 2:** Most respondents (69.3%) reported using GenAI for SE tasks once or multiple times per day. In contrast, only 35.7% of those who considered themselves somewhat proficient reported daily GenAI usage, suggesting a link between consistent use and perceived proficiency. Respondents who used GenAI more frequently also reported applying it across a larger number of SE tasks. Analyzing tool adoption from a given predefined list of options (with an open-ended "Other(s)" option), OpenAI's ChatGPT led reported tool adoption (83.1%), followed by GitHub Copilot (43.7%), Google's Gemini (35.2%), and Anthropic's Claude (32.4%). Open-weight models such as Deepseek-R1 (12.7%) and the Llama family of models (7%) showed more modest adoption. The use of AI-integrated development environments (besides GitHub Copilot) was reported by 19.7% of the participants. Examples include Cursor (6), Windsurf (1), and JetBrains AI Assistant (1).

**Finding 3:** The vast majority of practitioners (83.1%) reported using ChatGPT for SE tasks, which was nearly 2× higher than the next most popular tool (GitHub Copilot with 43.7%), suggesting that it has established itself as the leading platform for AI-assisted software development.

When interacting with GenAI tools for SE tasks, an equivalent number of participants reported using tools with a web interface (46, 63.9%) and IDE-integrated solutions (45, 62.5%). Other GenAI integrations such as GenAI APIs (14, 19.4%) and command line tools showed lower adoption (13, 18.3%). Despite having used GenAI for development tasks, five respondents (6.9%) indicated they had not been incorporated it into their workflows. A majority of practitioners (39, 54.2%) reported integrating GenAI into their workflows in two or more ways, while 28 (38.9%) reported a single integration, most commonly IDE-based (13) or web-based (12). Among participants using two integration types, 66.7% (20) reported using both web-based and IDE-integration. These findings suggest that practitioners who engage more frequently with GenAI tend to adopt more diverse integration strategies.

| GenAI Integration | # of Users | Percentage |
|---|---|---|
| No integration | 5 | 6.9% |
| Single integration | 28 | 38.9% |
| Dual integration | 30 | 41.7% |
| Triple integration | 6 | 8.3% |
| Four integrations | 3 | 4.2% |

**Table 2: Distribution of participants by number of GenAI workflow integrations (Web, IDE, Command line, and API)**

**Finding 4:** Practitioners reported no preference between incorporating web- or IDE-based GenAI tools into their development workflows, but did overwhelmingly employ one or both over command-line and API-based tools. Those who reported using GenAI tools multiple times a day were also more likely to incorporate GenAI tools into their workflows in multiple ways (Web-based, IDE-integration, etc.). This suggests that frequent GenAI users may develop more tailored or complex workflows.

#### 3.1.3 Changes in Development Approaches with GenAI.

When asked if GenAI tools had changed their approach to software development, the majority of respondents (55/71, 77.5%) indicated that they had experienced at least some change, while 7.0% were unsure and 15.5% reported no change. We asked respondents who reported experiencing changes to their development approach to elaborate on those changes. Nine participants reported using GenAI tools for tasks that previously required internet searches (e.g., finding library documentation or searching Stack Overflow for code examples), and four reported using GenAI to assist in information retrieval tasks within their code base. Six indicated that GenAI can provide a starting point for projects, such as helping with ideation (3), initial project design (5), or writing boilerplate code (6). Five respondents noted that GenAI allowed them to shift development focus from repetitive coding tasks to "higher-level" tasks such as architecture design, and four respondents claimed that GenAI tools allowed them to write more documentation. Still others indicated that GenAI helps produce cleaner, more organized code (3), reduces the focus and memory required to complete coding tasks (2), allows for development with unfamiliar programming languages (2), and can assist in project configuration (2). GenAI tool adoption has also created new processes in practitioner workflows. For example, six respondents spend more time reviewing and verifying AI-produced output, and four indicated they now write more detailed prompts.

**Finding 5:** The majority of practitioners (77.5%) reported that GenAI has changed their approach to software development, primarily by replacing internet searches, enabling boilerplate code generation, and shifting focus toward higher-level tasks. However, respondents also noted that GenAI introduces new verification overhead and requires adaptation of existing workflows.

### 3.2 Prompting and Conversation Strategies

#### 3.2.1 Prompting Technique Familiarity.

Participants were asked about three prompting techniques identified by White et al. (Meta Language Creation, Output Automator, and Persona) [51] in addition to Meta-Prompting and Few-Shot Learning [42]. We included two additional techniques, Output Style and Condition Check, which we did not find adequately represented in prior work. Technique definitions were provided to participants and can be found in Table 3.

**Table 3: Prompting technique descriptions.**

| Technique | Description |
|---|---|
| Condition Check | Produce certain output when specific condition(s) are met |
| Few-Shot Learning | Providing examples to guide generation |
| Meta Lang. Creation | Adjusts the semantics of words, phrases, or symbols |
| Meta-Prompting | Having AI suggest better prompts for specific tasks |
| Output Automator | Generating scripts to implement solutions |
| Output Style | Make the AI's output follow a particular format or style |
| Persona | Ask AI to complete a task while acting as a certain role |

Our analysis of prompting technique familiarity reveals a clear hierarchy of adoption, as shown in Figure 3. We consider participants were familiar with a technique if they knew or used the technique (occasionally or regularly). Respondents reported overwhelming familiarity with the aforementioned prompting strategies. Nearly all respondents were familiar with the Few-Shot Learning (93%), Output Style (92%), and Persona (92%) techniques. The Meta Language Creation technique were the least familiar to participants (74%). Despite the high familiarity, reported respondent usages (either occasionally or regularly) were markedly lower. The Output Style (82%), Few-Shot Learning (75%), Persona (68%), and Condition Check (65%) strategies had the highest reported usage rates among respondents who were familiar with the respective strategies. Roughly half of respondents familiar with the Output Automator (51%) and Meta-Prompting (49%) strategies reported using them. The Meta Language Creation strategy had the lowest adoption rate (36%). The Output Style (54%) and Persona (44%) strategies were most likely to be used regularly, among participants who used them. Despite being least popular overall, 42% of respondents who used Meta Language Creation, use it regularly. Respondents most often reported using the Output Automator (75%), Condition Check (68%), and Meta-Prompting (68%) strategies only occasionally.

Figure 3: Prompting technique familiarity distribution

**Finding 6:** Respondents were highly familiar with all seven prompting strategies, with 74%–94% reporting familiarity. However, actual usage rates were notably lower, particularly for Meta-Prompting and Output Automator, where roughly half of familiar respondents reported using them.

**Table 4: Prompting technique familiarity and use by GenAI proficiency and SE experience categories.**

| Proficiency | Familiar % | Use % | Occ. Use % | Reg. Use % |
|---|---|---|---|---|
| Somewhat | 74.5 | 52.1 | 89.5 | 10.5 |
| Proficient | 83.9 | 60.1 | 62.8 | 37.2 |
| Very | 89.7 | 69.0 | 51.3 | 48.7 |
| Maximally | 95.9 | 68.1 | 34.4 | 65.6 |

| Experience | Familiar % | Use % | Occ. Use % | Reg. Use % |
|---|---|---|---|---|
| Junior | 85.1 | 58.0 | 67.5 | 32.5 |
| Intermediate | 87.7 | 63.7 | 45.4 | 54.7 |
| Senior | 86.5 | 62.6 | 66.7 | 33.3 |
| Veteran | 57.1 | 71.4 | 65.0 | 35.0 |

None of respondents' self-reported GenAI proficiency, years of software development experience, or GenAI proficiency and experience impacted relative familiarity ratings of prompting techniques (e.g., across proficiency groups, Output Style always had a higher familiarity than Meta Language Creation).

Table 4 reports the proportion of respondents who are familiar with, and use, the seven prompting techniques across GenAI proficiency and SE experience categories. Technique usage rates are further reported by occasional and regular use. The table reports total percentages by aggregating response counts across the techniques. The results show a clear pattern: both technique familiarity and usage (including occasional and regular use) consistently increase with self-reported proficiency. In other words, participants who considered themselves more proficient were also more likely to use prompting techniques more frequently. In contrast, analysis by practitioner experience reveals a different trend. With the exception of veterans, all experience groups show similar familiarity and usage rates. Veteran are the least familiar with prompting techniques, but among those who are familiar, they are the most likely to use them. Analyzing occasional versus regular technique usage, practitioners across all experience levels show consistent rates, except for intermediate practitioners, who reported over 60% increase in regular usage compared with their peers. This suggests that intermediate practitioners may be at a career stage where they are both open to adapting their workflows and sufficiently experienced to integrate GenAI effectively.

**Finding 7:** Familiarity and usage of prompting techniques increase with GenAI proficiency rather than years of development experience. Veteran practitioners are the least familiar with prompting techniques, yet the most likely to use the ones they know. While most experience groups use prompting at similar rates, intermediate practitioners stand out as especially active adopters, suggesting they are mid-career professionals that are uniquely positioned to integrate GenAI into their workflows.

#### 3.2.2 Prompt Information Inclusion.

We describe the prompt information practitioners use for each of the six SE tasks we studied. When prompting GenAI for code generation tasks, respondents (66) most often include example inputs and expected outputs (76%), a description of the desired functionality (73%), and relevant code snippets (68%). Less common information includes existing code to modify (48%), style guidelines (31%), and performance requirements (17%).

When using GenAI tools for refactoring tasks, respondents (23) most often include the original code with explanatory comments (78%), a description of the existing issues or refactoring goals (65%), and examples of similar code that they find to be well structured (61%). Others opt to include architectural constraints and style guidelines (48%), a specific refactoring pattern to apply (48%), or code that should remain unchanged during the refactoring (43%). The least common information supplied in respondent prompts include unit tests (22%) and performance requirements (17%).

Of the 28 respondents who use GenAI for testing tasks, 82% prompt the model with the code to be tested along with specifications. Respondents also include example test cases (46%), testing preferences (43%), information on edge cases or expected behaviors (39%), existing test suite examples (39%), and mocking instructions (36%) in their prompts. The least common to be included are test coverage goals (25%), environmental requirements (25%), and performance or resource constraints (14%).

When using GenAI for debugging tasks, nearly all respondents (94%) provide the model with full error messages or stack traces. Similarly, 81% often include related logs or console output. Less common context given to the model includes environmental details (50%), previously attempted solutions (44%), (bug) reproduction steps (41%), system architecture information (31%), and visual evidence of issue manifestation (e.g., screenshots) (25%). Only two respondents (6%) included version control history.

For documentation tasks, respondents (34) reported that they often provide the model with the code snippet along with a functionality explanation (71%). Some also provide examples highlighting the desired documentation style (53%), usage examples/scenarios (41%), context about the target audience (38%), existing documentation in need of updates (38%), format requirements (35%), guidance on domain-specific terminology (29%), and references to related documentation (26%).

For code review tasks, respondents (23) most often provide the code to be reviewed (91%), along with project or domain-specific context (65%) and coding standards or style guidelines (57%). Less common information includes the purpose or expected behavior of the code (48%), related code that interacts with the reviewed code (39%), performance requirements (30%), and security considerations (26%).

#### 3.2.3 Conversation Strategies.

We asked participants about nine conversation strategies they may use when interacting with GenAI tools. Figure 4 shows the distribution of these strategies. The most frequently used strategy was Incremental refinement (incrementally refining the same prompt) followed closely by Feedback loop (using potentially different prompts to achieve the desired result). These strategies reflect practitioners' preference for multi-turn conversations where they can guide and refine GenAI responses progressively. However, Single comprehensive prompt is the third most popular and does not reflect this iterative workflow. The least popular strategies were Comparative analysis, Template-based approach, and Exploratory dialogue. Despite their lower adoption rates, these strategies still showed meaningful usage patterns, with at least 40% of practitioners employing them "Sometimes" or "Often".

**Table 5: Conversation strategy with GenAI tools.**

| Conversation Strategy | Description |
|---|---|
| Comparative analysis | Having the AI generate multiple solutions for comparison |
| Context building | Adding more context as the conversation develops |
| Exploratory dialogue | AI explores multiple solutions before implementing one |
| Feedback loop | Providing feedback on AI responses to guide future outputs |
| Incremental refinement | Iterative refinement on basic request based on AI responses |
| Multi-part problem solving | Dividing the task into sub-problems addressed in sequence |
| Single comprehensive prompt | One prompt with all requirements, context, and constraints |
| Step-by-step guidance | Breaking problem down into sequential steps for AI to solve |
| Template-based approach | Applying prompt templates adapted for task |

#### 3.2.4 Error Handling Strategies.

We asked participants to indicate which error handling strategies they use when they deem GenAI responses as inadequate. Participants were provided with nine strategies and could select none or any number of strategies. Practitioners converge on two complementary strategies (Figure 5): providing additional context and pointing out specific issues, with 79% of frequent users employing both approaches. Figure 5 shows that reformulating requests, adding constraints, including example solutions, breaking down complex problems, and providing feedback on partial solutions show more moderate adoption, while requesting alternatives or explanations remain far less popular. However, the 13 respondents who often use this least popular strategy are likely to use every other strategy: none chose "Never" in response to any option. There is a similar trend for the 15 respondents who frequently request alternatives: only three selected "Never" for requesting explanations and not for any other strategy.

**Finding 8:** Practitioners who reported utilizing less popular error handling strategies typically also used all other provided strategies at least rarely. This suggests that strategies are used as complements to others.

We identified connections between conversation structuring and error handling approaches, focusing exclusively on users who responded "Often" to both types of strategies. 80% of practitioners who frequently use Incremental refinement also provide additional context when errors occur. Similarly, 83% of users who provide feedback on partial solutions frequently utilize Feedback loop. Those who use step-by-step guidance often break down complex problems when handling errors (50%). These correlations show consistent practitioner strategies, which could inform future tool design: for example, a tool might activate additional context provision settings if a practitioner is aware of their preference for an iterative strategy, or adjust a prompting agent's writing style depending on the user.

#### 3.2.5 Exchange Count.

We asked respondents to report the average number of exchanges (back-and-forth interactions) needed to complete SE tasks with GenAI tools. Survey options included predefined ranges (1, 2-3, 4-6, 7-10, 10+, and Unsure). No participants reported consistently completing tasks in a single exchange, suggesting that current GenAI systems require iterative interaction regardless of user expertise or strategy choice. Self-reported GenAI skill levels show a positive correlation with exchange count, as seen in Table 6. Maximally proficient users require substantially more exchanges than other skill levels, having by far the highest proportion of "10+" selections. Longer conversations also correlate with productivity gains: participants using 10+ exchanges were the only group to report exclusively positive productivity impacts, with 6/7 indicating "significant" improvements. This suggests that sustained engagement with GenAI tools may be necessary to realize their full potential.

**Table 6: Exchange count distribution by self-reported skill.**

| GenAI Skill Level | 2-3 | 4-6 | 7-10 | 10+ | Unsure |
|---|---|---|---|---|---|
| Somewhat Proficient | 3 | 7 | 0 | 0 | 4 |
| Proficient | 15 | 11 | 3 | 3 | 0 |
| Very Proficient | 5 | 9 | 1 | 1 | 2 |
| Maximally Proficient | 1 | 3 | 0 | 3 | 0 |
| Total | 24 | 30 | 4 | 7 | 6 |

**Finding 9:** No participants reported consistently completing SE tasks in a single exchange with GenAI. More proficient users tended to engage in longer conversations, with maximally proficient users requiring substantially more exchanges. Longer conversations correlated with greater productivity gains, suggesting sustained interaction is key to effective GenAI use.

### 3.3 Sub-task Usage and Reliability

#### 3.3.1 GenAI Sub-task Usage.

For each SE task, we asked respondents to select the specific sub-tasks for which they used GenAI. The results are summarized in Table 7.

**Table 7: Most frequently selected sub-tasks for each SE task. 'I' = Implementation focus (lower abstraction level) 'D' = Design / Review focus (higher abstraction level)**

| SE Task | Sub-task | Count |
|---|---|---|
| Code Generation | Impl. new code components (I) | 52 |
| Code Generation | Setting up structural code (I) | 34 |
| Code Generation | Designing software architectures (D) | 30 |
| Documentation | Code-level documentation (I) | 24 |
| Documentation | Project-level documentation (D) | 13 |
| Testing | Test creation and implementation (I) | 18 |
| Testing | Test strategy and planning (D) | 3 |
| Debugging | Bug fixing (I) | 26 |
| Debugging | Issue diagnosis (D) | 22 |
| Refactoring | Optimizing existing code (I) | 14 |
| Refactoring | Standardizing and cleaning code (D) | 12 |
| Review | Funct./perf. assessment (I) | 10 |
| Review | Code quality evaluation (D) | 7 |

For code generation, respondents showed a strong preference for using GenAI to implement new code components (52) and set up structural code (34), compared to designing software architectures (30). This reflects a clear preference for using GenAI to assist with sub-tasks related to implementation rather than design/analysis. A similar implementation-focus emerges for some of the other SE tasks. For example, for testing, respondents showed a pronounced 6:1 preference for test creation/implementation (18) over test strategy/planning; and for documentation, a nearly 2:1 preference for code-level documentation (24) over project-level documentation (13). A few additional GenAI sub-tasks were not included in our predefined options, including reverse engineering, background research, and input generation for tests, each highlighted by one respondent.

**Finding 10:** For code generation, documentation, and testing, respondents generally used GenAI for implementation-focused (lower-level) sub-tasks rather than for design and analysis (higher-level) sub-tasks.

#### 3.3.2 GenAI Perceived Reliability.

To assess practitioners' trust in GenAI tools, we analyzed reported reliability ratings for 12 scenarios spanning all six studied SE tasks. Participants rated each scenario on a 4-point scale from "Very unreliable" to "Very reliable," with "Unsure/Haven't tried" responses excluded from our analysis. Figure 6 shows the perceived reliability of using GenAI for various tasks. Respondents reported that documentation tasks were the most reliable to complete with GenAI. In particular, maintaining documentation accuracy received the highest avg. rating (3.06, n=32), followed by documenting implementation rationale (2.77, n=31). Respondents showed moderate confidence in using GenAI for testing and debugging tasks, including test case design and coverage (2.64, n=25) and root cause analysis of existing errors (2.57, n=30). The tasks reported as least reliable by practitioners often involved complex analysis or reasoning. These included the assessment of non-functional requirements (2.14, n=14), the modernizing of outdated code patterns (2.32, n=22), and the implementation of complex algorithms (2.38, n=66).

Figure 6: Reliability perceptions of GenAI across tasks

**Finding 11:** Respondents perceived GenAI as less reliable for software tasks requiring complex reasoning, analysis, and domain knowledge.

GenAI reliability results across respondents' experience and self-reported GenAI proficiency groups can be seen in Table 8. Participants were presented with subsets of the 12 reliability options from Figure 6, which varied based on the SE tasks they indicated using GenAI for. To account for this variation of presented options, we calculated proportions for each participant across all of their reliability responses, then calculated a reliability score as the mean of individual reliability ratings across each GenAI proficiency and experience category. Overall reliability scores were calculated by multiplying integer values for the Likert-scale options ("Very unreliable" = 1, "Very reliable" = 4) by the calculated proportion of a given category, then dividing the % of participants who gave a rating other than "Unsure." Overall reliability proportions and scores are reported in Table 8.

**Table 8: GenAI reliability results across GenAI proficiency and experience groups. ("Reliable" and "Unreliable" shortened to "+" and "-")**

| Experience | Very- | Some- | Some+ | Very+ | Unsure | Score |
|---|---|---|---|---|---|---|
| Junior | 7.1% | 22.7% | 44.8% | 12.8% | 12.7% | 2.73 |
| Intermed. | 12.2% | 37.4% | 36.0% | 4.4% | 10.1% | 2.36 |
| Senior | 16.2% | 35.3% | 34.7% | 2.6% | 11.2% | 2.27 |
| Veteran | 7.1% | 19.1% | 47.6% | 17.3% | 8.9% | 2.82 |

| Proficiency | Very- | Some- | Some+ | Very+ | Unsure | Score |
|---|---|---|---|---|---|---|
| Some. Prof. | 29.5% | 30.4% | 27.4% | 0% | 12.8% | 1.98 |
| Proficient | 6.2% | 33.1% | 42.8% | 11.3% | 6.6% | 2.63 |
| Very Prof. | 8.4% | 26.9% | 37.7% | 10.2% | 16.7% | 2.60 |
| Max. Prof. | 4.8% | 29.1% | 46.7% | 4.1% | 15.5% | 2.59 |

**Finding 12:** Senior practitioners (with 11-20 years of development experience) find GenAI least reliable on average, while veterans (with 21+ years) find it most reliable on average.

#### 3.3.3 Issue Frequency.

Our final reliability analysis examined how frequently practitioners encountered specific issues (given to them) when using GenAI tools across different SE contexts. Participants rated twelve task-specific issues on a five-point scale from "Always" (1) to "Never" (5), where lower mean scores indicate more frequent issue occurrence. Results are visualized in Figure 7. Debugging emerges as the most problematic SE task, with suggested bug fixes missing the root cause having the highest issue frequency (2.34, n=32). This issue received four "Always" responses (the highest count for any absolute rating across all issues, despite only appearing for those who selected the task), indicating that GenAI's diagnostic capabilities remain a critical hurdle. Refactoring and code generation follow in severity, with unintended changes to behavior (2.52, n=23) and correctness/compatibility issues in code (2.58, n=66) representing significant challenges. Documentation and code review showed the lowest reported issue frequencies, with practitioners noticing inaccurate or incomplete technical documentation (3.06, n=34) and false positives and hallucinations (3.00, n=23) least often. This aligns with our previous findings about the lower complexity of these tasks.

**Finding 13:** Respondents reported experiencing the most issues when using GenAI for debugging, particularly when it fails to provide root causes. Documentation and code review tasks showed the fewest issues, consistent with their higher perceived reliability.

**Table 9: GenAI issue frequency ranking across SE tasks.**

| Rank | Issue | Mean | n |
|---|---|---|---|
| 1 | Suggested bug fixes miss root causes | 2.34 | 32 |
| 2 | Unintended behavior changes | 2.52 | 23 |
| 3 | Code correctness and compatibility issues | 2.58 | 66 |
| 4 | Incomplete code transformations | 2.61 | 23 |
| 5 | Fixes that introduce new bugs | 2.63 | 32 |
| 6 | Codebase consistency issues | 2.70 | 66 |
| 7 | Superficial explanations of functionality | 2.76 | 34 |
| 8 | Low-value tests with inadequate coverage | 2.82 | 28 |
| 9 | Superficial code analysis | 2.87 | 23 |
| 10 | Tests that miss actual requirements | 2.89 | 28 |
| 11 | False positives and hallucinations | 3.00 | 23 |
| 12 | Inaccurate or incomplete documentation | 3.06 | 34 |

## 4. Discussion

### 4.1 Developing Proficiency with Generative AI

Our results show a positive relationship between a practitioner's perceived GenAI proficiency and the number of tasks they complete with GenAI (Table 1), suggesting that task diversity and GenAI proficiency may mutually reinforce each other. This could potentially reflect how confidence encourages practitioners to explore GenAI usage in new contexts, or could also demonstrate that using GenAI on a wide range of tasks increases proficiency.

Users' prompt construction strategies vary significantly among tasks. Respondents showed a high consensus in the information they reported providing to models when completing debugging tasks, with 94% including full error messages/stack traces. By contrast, there was little agreement on the information included for documentation tasks, despite those being the second most common SE tasks completed with GenAI assistance: only 71% (24/34) of respondents reported providing the model with the code snippet and a functionality explanation. Code Generation has the next lowest with 76% of respondents including example inputs and expected outputs. All tasks show some convergence of information inclusion strategies, and debugging and testing (which have the highest agreement) explicitly involve work on existing code, making that necessary to share in most instances. However, Documentation also involves work on existing code in many cases, suggesting that consensus differences have no clear pattern.

One counterintuitive finding is that maximally proficient users require substantially more exchanges to complete tasks than less skilled users (Table 6), which seems to indicate that higher skill correlates with inefficiency. Another interpretation is that the strategies employed by these high-skill users are not inefficient, but naturally result in more prompts by enabling users to tackle more ambitious problems. Notably, longer conversations correlate with productivity gains: participants using 10+ exchanges were the only group to report exclusively positive productivity impacts, with 6/7 indicating "significant" improvements. This suggests that sustained engagement with GenAI tools may be necessary to realize their full potential.

### 4.2 Reliability and Error Patterns

Our findings reveal that practitioners perceive GenAI as most reliable for documentation tasks and least reliable for complex coding tasks such as debugging and implementing complex algorithms. This aligns with the inherent complexity of these tasks: code generation and debugging require understanding of code semantics, system architecture, and the effects of modifications, compared to natural language tasks such as documentation and review. While these results provide some direction for the critical problems GenAI engineers should focus on solving, others point toward alternative ways to improve reliability and user experience. Table 6 shows how the number of GenAI exchanges increases with a user's skill, and users tend to prefer iterative conversations (Section 3.2.4). Accordingly, high-profile tools usually facilitate iteration in some respect, most obviously by allowing users to send multiple prompts throughout a conversation. However, there are other ways to facilitate iteration, such as allowing users to edit earlier prompts to create conversation branches.

Our findings indicate that daily use makes productivity improvements significantly more likely (Section 3.1.2), and also correlates with GenAI use on a broader range of tasks. This suggests that the best way for individual practitioners to realize the benefits of these new tools is to carefully consider which tasks in their workflow could benefit from utilizing GenAI, then purposefully learn about and apply GenAI there. Gradual adjustment may be necessary to ensure consistent performance and build an understanding of how best to navigate AI limitations.

### 4.3 High Technique Awareness, Low Adoption

Our survey population had an overwhelming familiarity with various prompting techniques, with their awareness of the Meta Language Creation technique being the lowest (74%). However, despite an overall high awareness, there was a lackluster adoption. For example, even though 92% (66/72) of respondents indicated familiarity with the Output Style technique, only 82% of those (54) actually used it at all, and of those only 54% (29) used it regularly. The adoption percentages are worse for the remaining techniques, and regular usages are well below 50%. This is particularly interesting given that awareness of research outcomes is typically one of the strongest predictors of adoption in other contexts. One explanation may be that practitioners develop their own ad-hoc prompting strategies through trial and error rather than adopting formal techniques from the literature. Another possibility is that the techniques described in academic literature do not map well to the practical needs of software developers. Future work should investigate whether formal training in prompting techniques leads to measurable improvements in GenAI-assisted development outcomes.

### 4.4 Implications for Tool Design and Education

Our findings have several implications for the design of GenAI tools and for education around their use. First, the strong correlation between proficiency and task breadth suggests that tools should help novice users discover additional use cases. For example, a tool might suggest documentation or refactoring workflows to users who primarily use code generation. Second, the prevalence of multi-turn conversations and the correlation between exchange count and productivity suggest that tools should be optimized for iterative interaction, including features such as conversation branching, prompt templates, and contextual memory across sessions. Third, the gap between technique awareness and adoption suggests that techniques should be embedded directly into tool interfaces rather than relying on users to learn them independently.

## 5. Threats to Validity

**Internal Validity.** To mitigate possible coding biases, we used a rigorous iterative open-coding methodology to analyze open-ended survey responses. We also followed the best practices when formulating our survey questions in order to avoid confusing and/or biasing language, and conducted a small pilot study with graduate students to test the clarity and length of our questionnaire. We recruited participants from a variety of sources (our professional networks, university organizations, etc.) to ensure we received a broad range of perspectives and experiences, but we are aware of the threat of self-selection bias.

**External Validity.** Study conclusions apply only to participants who completed our survey and cannot be generalized to larger practitioner populations. However, given the themes and trends that emerged, we believe that many practitioners will share similar experiences to those reported. Ultimately, our goal was never to claim generalizability, but to explore the emerging landscape of how practitioners are interacting with GenAI tools for SE tasks.

**Construct Validity.** Some survey questions relied on self-reported data, which may be subject to recall bias or social desirability effects. We mitigated this by ensuring anonymity and by using validated survey design principles. Additionally, the prompting techniques we asked about were based on a catalog from the literature, which may not capture all techniques practitioners use in practice.

## 6. Related Work

The proliferation of LLMs and their integration into software development have led to a new design paradigm of integrated, interacting commands with more traditional structured code [29, 47]. Multiple reviews of LLM [16, 20] and LLM-based agents [32] for SE show extensive possibilities to further improve SE workflows. This has created the field of prompt engineering, which serves to determine the most effective ways of prompting a model in order to produce high-quality output which suits the user's needs. In its early stages, this resulted in explorations of individual strategies, leading to catalogs of prompt patterns [51] applicable to a broad range of interaction types [49]. As more patterns were refined, improved and discovered, compilations of techniques were formed through extensive reviews of the academic literature [41, 42], though empirical analysis has found no significant differences in code quality across basic prompt patterns [13]. Others attempted to apply prompt engineering for specific applications such as security [48], design more complex conversational workflows [39], and even use the generative AI models themselves for prompt engineering tasks [56]. With new advances such as chain-of-thought outputs [50], human-AI interaction is evolving beyond just prompting.

Although these frameworks and pattern collections have provided an important foundation for understanding prompting capabilities, they reveal little about how software developers use AI tools in practice. The DevGPT dataset [53] and various analyses of it have sought to close this gap, but often focus on a broader analysis of collaborative contexts [19], specific tasks such as issue resolution [14], or high-level usage patterns such as autocomplete / coding acceleration [30] rather than an examination encompassing diverse types of SE tasks. Li et al. conducted a comprehensive study on the individual and organizational motives of AI adoption and use among software developers [28], while Simaremare et al. highlighted the need for systematic investigation into real-world prompting practices.

## 7. Conclusion

We conducted a comprehensive survey of 72 software practitioners to investigate how they integrate GenAI tools into software engineering workflows. Our findings reveal primary adoption of GenAI for code generation, while use for related tasks such as documentation and debugging strongly correlates with a practitioner's AI proficiency and usage frequency. Users tend to prefer iterative conversations to achieve their goals, with consistent single-shot prompting remaining an impossibility. Significant reliability challenges remain for complex coding tasks, particularly debugging.

Our study identified 13 key findings that characterize how practitioners use GenAI in practice. While familiarity with prompting techniques is high, actual adoption remains low, suggesting a need for better integration of techniques into tool interfaces. Practitioners perceive documentation tasks as most reliable and debugging as least reliable, with issue frequency data confirming this pattern. These findings provide actionable insights for tool designers seeking to improve human-AI interaction in software engineering, and for educators developing curricula around the evolving skill set needed for effective GenAI collaboration.

## References

[1] [n.d.]. Qualtrics. https://www.qualtrics.com/. Accessed: 2025-10-07.

[2] Eman Abdullah AlOmar, Anushkrishna Venkatakrishnan, Mohamed Wiem Mkaouer, Christian Newman, and Ali Ouni. 2024. How to refactor this code? an exploratory study on developer-chatgpt refactoring conversations. In Proceedings of the 21st International Conference on Mining Software Repositories. 202–206.

[3] Isaac Alpizar-Chacon and Hieke Keuning. 2025. Student's Use of Generative AI as a Support Tool in an Advanced Web Development Course. In Proceedings of the 30th ACM Conference on Innovation and Technology in Computer Science Education V. 1. 312–318.

[4] Muhammad Rizky Anditama and Achmad Nizar Hidayanto. 2024. Analysis of Factors Influencing the Adoption of Artificial Intelligence Assistants among Software Developers. https://doi.org/10.33022/ijcs.v13i4.4239

[5] Anthropic. [n.d.]. ClaudeCode https://code.claude.com/docs/en/overviewt. Last accessed: January 2026.

[6] Berk Atil, Sarp Aykent, Alexa Chittams, Lisheng Fu, Rebecca J. Passonneau, Evan Radcliffe, Guru Rajan Rajagopal, Adam Sloan, Tomasz Tudrej, Ferhan Ture, Zhe Wu, Lixinyu Xu, and Breck Baldwin. 2025. Non-Determinism of "Deterministic" LLM Settings. arXiv: 2408.04667 [cs.CL] https://arxiv.org/abs/2408.04667

[7] Manaal Basha and Gema Rodríguez-Pérez. 2025. Trust, transparency, and adoption in generative AI for software engineering: Insights from Twitter discourse. Information and Software Technology 186 (2025), 107804. https://doi.org/10.1016/j.infsof.2025.107804

[8] Jenna Butler, Jina Suh, Sankeerti Haniyur, and Constance Hadley. 2024. Dear Diary: A randomized controlled trial of Generative AI coding tools in the workplace. arXiv: 2410.18334 [cs.SE] https://arxiv.org/abs/2410.18334

[9] Rudrajit Choudhuri, Ambareesh Ramakrishnan, Amreeta Chatterjee, Bianca Trinkenreich, Igor Steinmacher, Marco Gerosa, and Anita Sarma. 2025. Insights from the frontline: GenAI utilization among software engineering students.

[10] [Additional references as in original paper]

[11]–[56] [See original paper for complete reference list]
