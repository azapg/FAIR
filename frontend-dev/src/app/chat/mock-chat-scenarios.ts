import type { Message } from "@/lib/chat-contract"

export interface Scenario {
  id: string
  title: string
  description: string
  messages: Message[]
}

export const mockScenarios: Scenario[] = [
  {
    id: "none",
    title: "None (Empty)",
    description: "Clears the chat state.",
    messages: []
  },
  {
    id: "data-viz-complex",
    title: "Student: Data Analysis Agent",
    description: "Data analysis scenario showing complex CoT, tool errors, retries, and canvas widgets.",
    messages: [
      {
        id: "m1",
        role: "user",
        senderName: "Student Researcher",
        timestamp: "7:07 PM",
        content: "Can you create a plot of all TB cases over time per region? Also add a trend line. Here is the dataset.",
        attachments: [
          { name: "TB Burden Country Data.csv", size: "342 KB", type: "CSV", isImage: false }
        ]
      },
      {
        id: "m2",
        role: "assistant",
        senderName: "Data Analyst",
        timestamp: "7:09 PM",
        content: "I have successfully loaded and parsed the CSV file [2]. The dataset contains 5,120 rows tracking estimates of TB incidence from 1990 onwards.\n\nAfrican region (AFR) and South-East Asia (SEA) show the highest total incident cases, while other regions show a steady decline [1]. I've generated an interactive plot for you to explore.",
        events: [
          { type: "thought", content: "The user wants a plot of TB cases over time grouped by region, including a trend line. I need to load the attached CSV first to see the column names.", durationMs: 1200 },
          { type: "tool_call", toolName: "run_command", args: { command: "head -n 5 'TB Burden Country Data.csv'" }, status: "completed", resultSummary: "Columns: Country, Region, Year, e_inc_num, e_pop_num" },
          { type: "thought", content: "Great. The relevant columns are 'Region', 'Year', and 'e_inc_num' (estimated incidence). I will write a quick pandas script to aggregate this data.", durationMs: 2500 },
          { type: "tool_call", toolName: "run_command", args: { command: "python -c 'import pandas as pd; df=pd.read_csv(\"TB Burden Country Data.csv\")'" }, status: "failed", resultSummary: "FileNotFoundError: 'TB Burden Country Data.csv'" },
          { type: "thought", content: "Wait, the file wasn't found in the current working directory. It might be in the attachments folder. Let me check the directory contents.", durationMs: 800 },
          { type: "tool_call", toolName: "run_command", args: { command: "ls ./attachments/" }, status: "completed", resultSummary: "TB Burden Country Data.csv" },
          { type: "thought", content: "Found it. I will run the aggregation and generate the JSON payload for the UI canvas widget.", durationMs: 3100 },
          { type: "tool_call", toolName: "run_command", args: { command: "python ./scripts/aggregate_tb_data.py --input ./attachments/'TB Burden Country Data.csv'" }, status: "completed", resultSummary: "Successfully aggregated 5,120 rows into 6 regional time series." }
        ],
        sources: [
          { index: 1, title: "WHO Tuberculosis Report", url: "https://www.who.int/teams/global-tuberculosis-programme/data", snippet: "Global TB burden database.", type: "web" },
          { index: 2, title: "TB Burden Country Data.csv", snippet: "Local dataset containing 5,120 rows.", type: "file" }
        ],
        canvasContent: {
          title: "TB Cases Over Time by Region",
          type: "Python · Plotly",
          visualType: "chart",
          code: `import pandas as pd\nimport plotly.express as px\n\ndf = pd.read_csv("TB Burden Country Data.csv")\ngrouped = df.groupby(["Region", "Year"])["e_inc_num"].sum().reset_index()\nfig = px.line(grouped, x="Year", y="e_inc_num", color="Region", title="TB Incidence")\nfig.show()`,
          data: {
            regions: ["AFR", "AMR", "EMR", "EUR", "SEA", "WPR"],
            years: [1990, 1995, 2000, 2005, 2010],
            series: {
              AFR: [85, 75, 70, 60, 55],
              AMR: [20, 25, 15, 5, 0],
              EMR: [50, 55, 50, 55, 60],
              EUR: [75, 72, 70, 78, 72],
              SEA: [80, 83, 79, 86, 83],
              WPR: [85, 88, 89, 93, 95]
            }
          }
        },
        statusPulse: { message: "Generating plotly visualization", elapsed: "32s" }
      }
    ]
  },
  {
    id: "batch-grade-orchestration",
    title: "Professor: Orchestrator Agent",
    description: "Scenario illustrating sub-agents, live status pulses, and human-in-the-loop validation.",
    messages: [
      {
        id: "bg1",
        role: "user",
        senderName: "Professor Allan",
        timestamp: "8:00 AM",
        content: "Grade all HW3 submissions using the rubric I uploaded. Flag anything under 0.8 confidence for my review.",
        attachments: [
          { name: "hw3_rubric.json", size: "1.2 KB", type: "JSON", isImage: false }
        ]
      },
      {
        id: "bg2",
        role: "assistant",
        senderName: "Grading Coordinator",
        timestamp: "8:04 AM",
        content: "Grading complete — 32 submissions processed. Class median: **74 / 100**. The distribution dashboard is above. Four submissions had AI confidence below 0.8 and are flagged for your review [1].",
        events: [
          { type: "thought", content: "I need to parse the hw3_rubric.json and apply it to the 32 submissions in the HW3 folder. I will delegate the grading to sub-agents to process them in parallel.", durationMs: 400 },
          { type: "tool_call", toolName: "read_file", args: { path: "hw3_rubric.json" }, status: "completed", resultSummary: "Loaded rubric containing 5 criteria." },
          { type: "tool_call", toolName: "list_dir", args: { path: "submissions_hw3/" }, status: "completed", resultSummary: "Found 32 PDF submissions." },
          { type: "thought", content: "I will invoke 32 grading sub-agents. I'll need to wait for them to finish and compile the ledger.", durationMs: 1100 },
          { type: "tool_call", toolName: "invoke_subagents", args: { count: 32, type: "grader" }, status: "running", resultSummary: "Spawning 32 grading sub-agents..." },
          { type: "tool_call", toolName: "invoke_subagents", args: {}, status: "completed", resultSummary: "All 32 agents finished. 4 submissions flagged with confidence < 0.8." },
          { type: "artifact_update", action: "create", artifactName: "grading_ledger.csv", diff: { added: 33, removed: 0 } }
        ],
        sources: [
          { index: 1, title: "Grading confidence ledger", snippet: "Raw log of confidence margins calculated by the parser model.", type: "file" }
        ],
        elicitation: {
          id: "int-grading",
          questions: [
            {
              id: "q1",
              title: "Decision needed — 4 low-confidence submissions",
              options: [
                { label: "Accept provisional grades", value: "accept" },
                { label: "Review each manually", value: "review" },
                { label: "Re-run with strict rules", value: "strict" }
              ]
            }
          ]
        },
        canvasContent: {
          title: "HW3 Score Distribution Dashboard",
          type: "Professor · Grade distribution",
          visualType: "chart",
          data: {
            regions: ["Grade Bands"],
            years: [1, 2, 3, 4, 5],
            series: {
              "A (90-100)": [5, 5, 5, 5, 5],
              "B (80-89)": [12, 12, 12, 12, 12],
              "C (70-79)": [8, 8, 8, 8, 8],
              "D (60-69)": [4, 4, 4, 4, 4],
              "F (<60)": [3, 3, 3, 3, 3]
            }
          }
        }
      }
    ]
  },
  {
    id: "student-code-debug",
    title: "Student: Code Sandbox",
    description: "Student needs help fixing a bug in their programming assignment. Agent uses sandbox execution and artifact editing.",
    messages: [
      {
        id: "scd1",
        role: "user",
        senderName: "Student",
        timestamp: "2:05 PM",
        content: "My sorting algorithm is failing on the autograder. Can you look at my code?",
        attachments: [
          { name: "mergesort.py", size: "2 KB", type: "file", isImage: false }
        ]
      },
      {
        id: "scd2",
        role: "assistant",
        senderName: "Teaching Agent",
        timestamp: "2:06 PM",
        content: "Your code looks close, but it's failing when the list contains duplicate numbers. I've created an artifact with a proposed fix. Notice what happens in your `merge` function when `left[i] == right[j]`.",
        events: [
          { type: "thought", content: "Let's read the student's code and run it in a sandbox against the hidden test suite.", durationMs: 1000 },
          { type: "tool_call", toolName: "read_file", args: { path: "mergesort.py" }, status: "completed", resultSummary: "Read 42 lines." },
          { type: "tool_call", toolName: "run_command", args: { command: "python -m unittest tests.test_mergesort" }, status: "failed", resultSummary: "FAIL: test_duplicates... AssertionError: Lists differ: [1, 2, 3] != [1, 2, 2, 3]" },
          { type: "thought", content: "Ah, the student missed the equality case in the merge loop. I will generate an artifact showing the diff, but I will only guide them to it rather than just giving the answer directly.", durationMs: 4500 },
          { type: "artifact_update", action: "create", artifactName: "mergesort_fix.py", diff: { added: 3, removed: 1 } }
        ],
        canvasContent: {
          title: "mergesort.py",
          type: "Python · Code",
          visualType: "code",
          code: `def merge(left, right):\n    result = []\n    i = j = 0\n    while i < len(left) and j < len(right):\n        if left[i] < right[j]:\n            result.append(left[i])\n            i += 1\n        elif left[i] > right[j]:\n            result.append(right[j])\n            j += 1\n    # missing equal case!\n    result.extend(left[i:])\n    result.extend(right[j:])\n    return result`
        }
      },
      {
        id: "scd3",
        role: "user",
        senderName: "Student",
        timestamp: "2:08 PM",
        content: "Oh, I only have `if left[i] < right[j]` and `elif left[i] > right[j]`. I didn't handle the equal case!"
      }
    ]
  },
  {
    id: "stress-regrade",
    title: "Professor: Regrade Stress Test",
    description: "Stress test scenario for advanced agent actions: delegation, parallel sub-agents, web search, interrupts.",
    messages: [
      {
        id: "stress_user_1",
        role: "user",
        senderName: "Professor",
        timestamp: "2026-07-08T14:00:00Z",
        content: "Regrade all Essay 2 submissions with the updated rubric, but first make sure the rubric matches what's posted, and check on Maria's late submission before you touch her grade."
      },
      {
        id: "msg_stress_regrade_essay2_part1",
        role: "assistant",
        senderName: "Grading Coordinator",
        timestamp: "2026-07-08T14:00:27Z",
        content: "Which rubric should I use — the stored version (3 pts for Sources) or the posted version (5 pts)? I'll hold the Sources grading until you decide.",
        events: [
          {
            id: "evt_01",
            type: "thought",
            timestamp: "2026-07-08T14:00:02Z",
            playbackDelayMs: 400,
            content: "Break this into three parts: verify the rubric is current, resolve Maria's late-submission status, then batch-grade the rest.",
          },
          {
            id: "evt_02",
            type: "tool_call",
            timestamp: "2026-07-08T14:00:06Z",
            playbackDelayMs: 600,
            toolName: "read_rubric",
            category: "data_read",
            args: { assignmentId: "essay-2" },
            status: "completed",
            label: "Read rubric for Essay 2",
            result: { version: "stored-v3", sections: 4, totalPoints: 100 },
          },
          {
            id: "evt_03",
            type: "tool_call",
            timestamp: "2026-07-08T14:00:11Z",
            playbackDelayMs: 500,
            toolName: "get_course_info",
            category: "data_read",
            args: { courseId: "eng-201" },
            status: "completed",
            label: "Checked posted rubric link on course page",
            result: { postedRubricVersion: "v4", postedAt: "2026-07-02" },
          },
          {
            id: "evt_04",
            type: "tool_call",
            timestamp: "2026-07-08T14:00:19Z",
            playbackDelayMs: 3800,
            toolName: "web_search",
            category: "web_search",
            args: { query: "MLA 9th edition citation rubric standard" },
            status: "completed",
            label: "Checked current MLA 9 citation rules",
            result: { source: "mla.org", summary: "confirms in-text citation format referenced in rubric" },
          },
          {
            id: "evt_05",
            type: "tool_call",
            timestamp: "2026-07-08T14:00:24Z",
            playbackDelayMs: 500,
            toolName: "verify_rubric_alignment",
            category: "validation",
            args: { stored: "stored-v3", posted: "v4" },
            status: "completed",
            label: "Found mismatch between stored and posted rubric",
            result: { mismatch: true, section: "Sources", storedPoints: 3, postedPoints: 5 },
          },
          {
            id: "evt_06",
            type: "thought",
            timestamp: "2026-07-08T14:00:26Z",
            playbackDelayMs: 400,
            content: "Section 3 (Sources) is worth 3 points in the stored rubric but 5 in the posted version. Silently picking one could change every grade. Flag it.",
          }
        ],
        elicitation: {
          id: "eli_rubric_mismatch",
          questions: [
            {
              id: "q_rubric",
              title: "Rubric Mismatch Detected",
              options: [
                { label: "Use posted version (5 pts)", value: "posted" },
                { label: "Use stored version (3 pts)", value: "stored" }
              ]
            }
          ]
        }
      },
      {
        id: "msg_stress_regrade_essay2_part2",
        role: "assistant",
        senderName: "Grading Coordinator",
        timestamp: "2026-07-08T14:06:14Z",
        content: "Graded 39 of 40 Essay 2 submissions. Maria's submission was late but inside her approved extension, so no penalty applied; I drafted a note to her but haven't sent it. One file, submission_23.pdf, wouldn't parse and needs a manual look.",
        events: [
          {
            id: "evt_08",
            type: "tool_call",
            timestamp: "2026-07-08T14:00:41Z",
            playbackDelayMs: 2500,
            toolName: "get_student_record",
            category: "data_read",
            args: { studentName: "Maria Chen", fetchHistory: true },
            status: "completed",
            label: "Checked Maria's extension status and history",
            result: { extensionApproved: true, extensionUntil: "2026-07-07T23:59:00Z" },
          },
          {
            id: "evt_09",
            type: "tool_call",
            timestamp: "2026-07-08T14:00:47Z",
            playbackDelayMs: 2200,
            toolName: "check_course_calendar",
            category: "calendar",
            args: { courseId: "eng-201", syncExternal: true },
            status: "completed",
            label: "Cross-checked submission time against updated calendar",
            result: { submittedAt: "2026-07-08T01:52:00Z", withinExtension: true },
          },
          {
            id: "evt_10",
            type: "tool_call",
            timestamp: "2026-07-08T14:00:55Z",
            playbackDelayMs: 8000,
            toolName: "web_search",
            category: "web_search",
            args: { query: "Maria Chen academic integrity violations prior semester" },
            status: "completed",
            label: "Scanned academic integrity database for prior flags",
            result: { flags: 0, status: "clear" },
          },
          {
            id: "evt_11",
            type: "tool_call",
            timestamp: "2026-07-08T14:01:05Z",
            playbackDelayMs: 4000,
            toolName: "delegate_subagents",
            category: "delegation",
            args: { task: "deep_plagiarism_analysis", batch: "1-40", strict: true },
            status: "completed",
            label: "Delegated deep plagiarism analysis to 4 sub-agents",
            result: { subagentIds: ["sub_a", "sub_b", "sub_c", "sub_d"] },
          },
          {
            id: "evt_12",
            type: "tool_call",
            timestamp: "2026-07-08T14:01:10Z",
            playbackDelayMs: 12000,
            parentId: "evt_11",
            toolName: "run_command",
            category: "code_execution",
            args: { subagent: "sub_a", command: "python cross_ref.py --batch=1-10 --deep" },
            status: "completed",
            label: "Sub-agent A running cross-reference NLP engine (Batch 1-10)",
            result: { completed: true, flagged: 0 },
          },
          {
            id: "evt_13",
            type: "tool_call",
            timestamp: "2026-07-08T14:01:10Z",
            playbackDelayMs: 15000,
            parentId: "evt_11",
            toolName: "run_command",
            category: "code_execution",
            args: { subagent: "sub_b", command: "python cross_ref.py --batch=11-20 --deep" },
            status: "completed",
            label: "Sub-agent B running cross-reference NLP engine (Batch 11-20)",
            result: { completed: true, flagged: 2 },
          },
          {
            id: "evt_14",
            type: "tool_call",
            timestamp: "2026-07-08T14:01:10Z",
            playbackDelayMs: 9000,
            parentId: "evt_11",
            toolName: "run_command",
            category: "code_execution",
            args: { subagent: "sub_c", command: "python cross_ref.py --batch=21-30 --deep" },
            status: "error",
            label: "Sub-agent C NLP engine crashed (OOM) on submission_23.pdf",
            result: { error: "Out of memory processing large file" },
          },
          {
            id: "evt_15",
            type: "thought",
            timestamp: "2026-07-08T14:01:25Z",
            playbackDelayMs: 2500,
            content: "Sub-agent C crashed due to OOM. I will isolate submission_23.pdf and restart the rest of batch 21-30 using a fresh subagent.",
          },
          {
            id: "evt_16",
            type: "tool_call",
            timestamp: "2026-07-08T14:01:27Z",
            playbackDelayMs: 11000,
            parentId: "evt_11",
            toolName: "run_command",
            category: "code_execution",
            args: { subagent: "sub_c_retry", command: "python cross_ref.py --batch=21-30 --exclude=23" },
            status: "completed",
            label: "Sub-agent C (Retry) finishing batch 21-30",
            result: { completed: true, flagged: 0 },
          },
          {
            id: "evt_17",
            type: "tool_call",
            timestamp: "2026-07-08T14:01:10Z",
            playbackDelayMs: 22000,
            parentId: "evt_11",
            toolName: "run_command",
            category: "code_execution",
            args: { subagent: "sub_d", command: "python cross_ref.py --batch=31-40 --deep" },
            status: "completed",
            label: "Sub-agent D running cross-reference NLP engine (Batch 31-40)",
            result: { completed: true, flagged: 1 },
          },
          {
            id: "evt_18",
            type: "status_pulse",
            timestamp: "2026-07-08T14:02:00Z",
            playbackDelayMs: 2000,
            content: "Plagiarism analysis complete. Delegating rubric grading...",
          },
          {
            id: "evt_19",
            type: "tool_call",
            timestamp: "2026-07-08T14:02:05Z",
            playbackDelayMs: 24000,
            toolName: "grade_student",
            category: "grading",
            args: { batch: "1-40", parallel: true, rubricPoints: 5 },
            status: "completed",
            label: "Grading all 40 submissions against rubric (5 pts per Source)",
            result: { graded: 39, failed: 1 },
          },
          {
            id: "evt_20",
            type: "status_pulse",
            timestamp: "2026-07-08T14:02:30Z",
            playbackDelayMs: 1500,
            content: "Grading 40 submissions… 39 of 40 complete",
          },
          {
            id: "evt_21",
            type: "artifact_update",
            timestamp: "2026-07-08T14:02:35Z",
            playbackDelayMs: 2000,
            content: "Grade distribution — Essay 2",
            result: { graded: 39, needsReview: 1, chartType: "histogram" },
          },
          {
            id: "evt_22",
            type: "tool_call",
            timestamp: "2026-07-08T14:02:40Z",
            playbackDelayMs: 8000,
            toolName: "draft_feedback_email",
            category: "communication",
            args: { studentName: "Maria Chen" },
            status: "completed",
            label: "Drafting custom feedback note to Maria (preview only)",
            result: { previewOnly: true, sent: false },
          },
          {
            id: "evt_23",
            type: "tool_call",
            timestamp: "2026-07-08T14:02:50Z",
            playbackDelayMs: 6500,
            toolName: "draft_feedback_email",
            category: "communication",
            args: { studentName: "John Doe", flags: 2 },
            status: "completed",
            label: "Drafting plagiarism warning note to John Doe",
            result: { previewOnly: true, sent: false },
          }
        ]
      }
    ]
  }
]
