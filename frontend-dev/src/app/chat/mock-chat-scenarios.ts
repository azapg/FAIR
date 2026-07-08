export interface MockMessage {
  id: string
  role: "user" | "assistant" | "system"
  senderName: string
  timestamp: string
  content: string
  attachments?: {
    name: string
    size: string
    type: string
    isImage?: boolean
    src?: string
  }[]
  tasks?: {
    title: string
    state: "pending" | "running" | "completed" | "failed"
    description?: string
  }[]
  statusPulse?: {
    message: string
    elapsed: string
  }
  elicitation?: {
    id: string
    questions: {
      id: string
      title: string
      options: { label: string; value: string }[]
    }[]
    resolved?: boolean
    selectedOption?: string
  }
  sources?: {
    title: string
    url?: string
    snippet?: string
    index: number
    type?: "web" | "file" | "doc"
  }[]
  canvasContent?: {
    title: string
    type: string
    code?: string
    visualType: "chart" | "simulation" | "code"
    data?: any
  }
}

export interface Scenario {
  id: string
  title: string
  description: string
  messages: MockMessage[]
}

export const mockScenarios: Scenario[] = [
  {
    id: "t1-student-concept",
    title: "Student: Concept Help",
    description: "T1: Simple, single-turn conversation explaining a concept without heavy tools.",
    messages: [
      {
        id: "t1-1",
        role: "user",
        senderName: "Student",
        timestamp: "10:00 AM",
        content: "I don't understand why the chain rule works intuitively. Can you show me?"
      },
      {
        id: "t1-2",
        role: "assistant",
        senderName: "Fair Tutor",
        timestamp: "10:02 AM",
        content: "Think of it like zooming in on a curve at a point until it looks straight. The chain rule says: if you stretch one function, then stretch the result by another function, the total stretch is the product of both rates.\n\nTry visualizing how the outer function \"scales\" the inner rate of change.",
        tasks: [
          {
            title: "exec(\"retrieve_concept('chain_rule', 'intuition')\")",
            state: "completed",
            description: "Fetched pedagogical framing: 'zooming in on a curve'."
          },
          {
            title: "exec(\"generate_analogy('chain_rule')\")",
            state: "completed",
            description: "Selected 'stretching functions' analogy."
          }
        ]
      }
    ]
  },
  {
    id: "tb-cases",
    title: "Student: Data Viz",
    description: "T2: Analytical scenario where an agent parses a CSV, generates summary statistics, and draws a chart.",
    messages: [
      {
        id: "tb1",
        role: "user",
        senderName: "Student Researcher",
        timestamp: "7:07 PM",
        content: "Can you create a plot of all TB cases over time per region? Also add a trend line. Here is the dataset.",
        attachments: [
          {
            name: "TB Burden Country Data.csv",
            size: "342 KB",
            type: "CSV"
          }
        ]
      },
      {
        id: "tb2",
        role: "assistant",
        senderName: "Analyst Agent",
        timestamp: "7:09 PM",
        content: "I have successfully loaded and parsed the CSV file [2]. The dataset contains 5,120 rows tracking estimates of TB incidence, prevalence, and mortality from 1990 onwards.\n\nAfrican region (AFR) and South-East Asia (SEA) show the highest total incident cases, while other regions show a steady decline [1]. I've generated an interactive plot for you to explore.",
        tasks: [
          {
            title: "read_file(\"TB Burden Country Data.csv\")",
            state: "completed",
            description: "Loaded target dataset CSV header structure."
          },
          {
            title: "exec(\"python -c 'import pandas as pd; df=pd.read_csv(\\\"TB Burden Country Data.csv\\\"); df.dropna(inplace=True)'\")",
            state: "completed",
            description: "Cleaned dataset, dropping 42 NaN values."
          },
          {
            title: "exec(\"python -c 'grouped = df.groupby([\\\"Region\\\", \\\"Year\\\"])[\\\"e_inc_num\\\"].sum()'\")",
            state: "completed",
            description: "Aggregating regional incident metrics using pandas."
          },
          {
            title: "exec(\"python -c 'import scipy.stats as stats; ...'\")",
            state: "completed",
            description: "Calculating regional case regression trend lines."
          }
        ],
        statusPulse: {
          message: "Aggregating regional incident metrics using pandas",
          elapsed: "32s"
        },
        sources: [
          {
            index: 1,
            title: "WHO Tuberculosis Report",
            url: "https://www.who.int/teams/global-tuberculosis-programme/data",
            snippet: "Global TB burden database and estimates of tuberculosis incidence, prevalence, and mortality.",
            type: "web"
          },
          {
            index: 2,
            title: "TB Burden Country Data.csv",
            snippet: "Local dataset containing 5,120 rows tracking annual incident tuberculosis rates.",
            type: "file"
          }
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
        }
      }
    ]
  },
  {
    id: "batch-grade",
    title: "Professor: Batch Grade",
    description: "T3: Orchestration scenario illustrating sub-agents, live status pulses, and human-in-the-loop validation.",
    messages: [
      {
        id: "bg1",
        role: "user",
        senderName: "Professor Allan",
        timestamp: "8:00 AM",
        content: "Grade all HW3 submissions using the rubric I uploaded. Flag anything under 0.8 confidence for my review.",
        attachments: [
          {
            name: "hw3_rubric.json",
            size: "1.2 KB",
            type: "JSON"
          }
        ]
      },
      {
        id: "bg2",
        role: "assistant",
        senderName: "Grading Coordinator",
        timestamp: "8:04 AM",
        content: "Grading complete — 32 submissions processed. Class median: **74 / 100**. The distribution dashboard is above. Four submissions had AI confidence below 0.8 and are flagged for your review [1].",
        tasks: [
          {
            title: "read_file(\"hw3_rubric.json\")",
            state: "completed",
            description: "Loaded target dataset rubric criteria."
          },
          {
            title: "read_file(\"submissions_hw3/\")",
            state: "completed",
            description: "Fetched 32 student submission files list."
          },
          {
            title: "exec(\"pdf_extract_text(submissions_hw3/*)\")",
            state: "completed",
            description: "Extracted raw text via OCR for all submissions."
          },
          {
            title: "exec(\"grade_submission × 32\")",
            state: "completed",
            description: "Spawning local grading sub-agents per student folder."
          },
          {
            title: "exec(\"compile_results_to_csv()\")",
            state: "completed",
            description: "Compiled all sub-agent results into a master ledger."
          }
        ],
        statusPulse: {
          message: "Working — 28 of 32 submissions graded",
          elapsed: "2m 14s"
        },
        sources: [
          {
            index: 1,
            title: "Grading confidence ledger",
            snippet: "Raw log of confidence margins calculated by the parser model.",
            type: "file"
          }
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
    id: "t4-course-material",
    title: "Professor: Course Material",
    description: "T4: Generative artifact chain creating slide decks and explainer videos.",
    messages: [
      {
        id: "t4-1",
        role: "user",
        senderName: "Professor Allan",
        timestamp: "9:00 AM",
        content: "Create a 12-slide intro to Newton's laws for first-year physics. Include a simulation slide and generate a short explainer video for each law."
      },
      {
        id: "t4-2",
        role: "assistant",
        senderName: "Content Creator",
        timestamp: "9:05 AM",
        content: "Slides and all three videos are ready. The videos have been embedded into the slide deck directly. Let me know if you want to tweak the video scripts before publishing.",
        tasks: [
          {
            title: "exec(\"generate_slides(topic='Newton\\'s laws', slides=12)\")",
            state: "completed",
            description: "Generated 12 PPTX slides outlining the 3 laws and examples."
          },
          {
            title: "exec(\"generate_video(prompt='Newton 1st Law inertia', duration=45s)\")",
            state: "completed",
            description: "Generated 45s explainer via Veo 3.1: hockey puck on frictionless ice."
          },
          {
            title: "exec(\"generate_video(prompt='Newton 2nd Law F=ma', duration=45s)\")",
            state: "completed",
            description: "Generated 52s explainer via Veo 3.1: pushing different masses."
          },
          {
            title: "exec(\"generate_video(prompt='Newton 3rd Law reaction', duration=45s)\")",
            state: "completed",
            description: "Generated 48s explainer via Veo 3.1: rocket propulsion."
          },
          {
            title: "write_file(\"newtons_laws_intro.pptx\")",
            state: "completed",
            description: "Compiled all media into the final PPTX presentation."
          }
        ],
        statusPulse: {
          message: "Rendering videos via Veo 3.1 API (Law 3/3)...",
          elapsed: "4m 12s"
        },
        canvasContent: {
          title: "Newton's Laws Intro Deck",
          type: "Presentation · PPTX",
          visualType: "code",
          code: `// Presentation Preview\nSlide 1: Title\nSlide 2: What is a force?\nSlide 3: First Law - Inertia\nSlide 4: Video 1 (Inertia)\nSlide 5: Second Law - F=ma\n...\nSlide 12: Summary`
        }
      }
    ]
  },
  {
    id: "diagnostic-KC",
    title: "Researcher: Diagnostic",
    description: "T5: Calculus diagnostic semantic clustering and knowledge component mapping, flagging new taxonomic items.",
    messages: [
      {
        id: "kc1",
        role: "user",
        senderName: "Researcher Allan",
        timestamp: "10:15 AM",
        content: "Analyze the calculus diagnostic test results for 200 students. Identify dominant error clusters and map them to the knowledge component taxonomy.",
        attachments: [
          {
            name: "diag_results.csv",
            size: "18 KB",
            type: "CSV"
          }
        ]
      },
      {
        id: "kc2",
        role: "assistant",
        senderName: "Researcher Assistant",
        timestamp: "10:17 AM",
        content: "I grouped the 200 responses into 7 clusters [1]. Six of the clusters map cleanly to the Calc_V2 Knowledge Component taxonomy. However, Cluster 6 (implicit chain rule errors) does not match any existing KC. Would you like to expand the taxonomy?",
        tasks: [
          {
            title: "read_file(\"diag_results.csv\")",
            state: "completed",
            description: "Loaded student diagnostic CSV answers."
          },
          {
            title: "exec(\"python run_embeddings.py --model text-embedding-3\")",
            state: "completed",
            description: "Generated 1536-dimensional embeddings for 200 student responses."
          },
          {
            title: "exec(\"python run_clustering.py --algorithm umap_kmeans\")",
            state: "completed",
            description: "Computed 7 KMeans centroids and 2D UMAP projection coordinates."
          },
          {
            title: "exec(\"python map_to_kc_taxonomy.py --taxonomy calc_v2\")",
            state: "completed",
            description: "Matched 5/7 clusters, 1 ambiguous, 1 completely new."
          }
        ],
        sources: [
          {
            index: 1,
            title: "Calculus KC Taxonomy Calc_V2",
            snippet: "Official map of calculus competencies and diagnostic tags.",
            type: "doc"
          }
        ],
        elicitation: {
          id: "int-kc",
          questions: [
            {
              id: "q1",
              title: "Cluster 6 does not match any existing KC. Add to taxonomy?",
              options: [
                { label: "Add to Taxonomy (Affects 23 students)", value: "add" },
                { label: "Ignore cluster", value: "ignore" }
              ]
            }
          ]
        },
        canvasContent: {
          title: "Error Cluster UMAP Projection",
          type: "Analysis · Plotly",
          visualType: "chart",
          data: {
             regions: ["C1 (Limits)", "C2 (Derivatives)", "C3 (Integration)", "C6 (Unknown)"],
             years: [1, 2],
             series: {
               "C1 (Limits)": [1.2, 3.4],
               "C2 (Derivatives)": [5.1, 2.2],
               "C3 (Integration)": [4.4, 6.7],
               "C6 (Unknown)": [8.8, 1.1]
             }
          }
        }
      }
    ]
  },
  {
    id: "t6-long-running-audit",
    title: "Professor: Long-running Audit",
    description: "T6: What 'long-running with multiple interrupts' looks like as a full conversation thread.",
    messages: [
      {
        id: "t6-1",
        role: "user",
        senderName: "Professor Allan",
        timestamp: "2:00 PM",
        content: "Run the full semester grading audit — all 8 assignments, flag outliers, and generate the final performance report for my 45 students."
      },
      {
        id: "t6-2",
        role: "assistant",
        senderName: "Audit Agent",
        timestamp: "2:08 PM",
        content: "I've started processing HW1 through HW8. During HW3 processing, I noticed an ambiguity.",
        tasks: [
          {
            title: "exec(\"fetch_assignments(course='CS101', assignments=8)\")",
            state: "completed",
            description: "Loaded 360 total submissions across 8 assignments."
          },
          {
            title: "exec(\"grade_batch(assignment='HW1')\")",
            state: "completed",
            description: "Graded HW1: Mean 82%"
          },
          {
            title: "exec(\"grade_batch(assignment='HW2')\")",
            state: "completed",
            description: "Graded HW2: Mean 79%"
          },
          {
            title: "exec(\"grade_batch(assignment='HW3')\")",
            state: "completed",
            description: "Processing HW3 - encountered derivation mismatch."
          }
        ],
        statusPulse: {
          message: "Processing HW3 — 45 submissions",
          elapsed: "6m 12s"
        },
        elicitation: {
          id: "int-audit-1",
          questions: [
            {
              id: "q1",
              title: "Which widget should I prototype first for FAIR's chat UI?",
              options: [
                { label: "Rubric result card", value: "rubric" },
                { label: "Grade distribution chart", value: "chart" },
                { label: "Feedback explainer", value: "feedback" },
                { label: "Confidence band indicator", value: "confidence" }
              ]
            },
            {
              id: "q2",
              title: "Who's the primary audience for this first prototype?",
              options: [
                { label: "Students", value: "students" },
                { label: "Teachers", value: "teachers" },
                { label: "Both equally", value: "both" }
              ]
            }
          ]
        }
      },
      {
        id: "t6-3",
        role: "user",
        senderName: "Professor Allan",
        timestamp: "2:09 PM",
        content: "Accept as valid"
      },
      {
        id: "t6-4",
        role: "assistant",
        senderName: "Audit Agent",
        timestamp: "2:13 PM",
        content: "Got it — awarding full credit to all 11 students on Q4. \n\nI continued processing up to HW6 and found a significant statistical outlier.",
        tasks: [
          {
            title: "exec(\"grade_batch(assignment='HW4')\")",
            state: "completed",
            description: "Graded HW4: Mean 85%"
          },
          {
            title: "exec(\"grade_batch(assignment='HW5')\")",
            state: "completed",
            description: "Graded HW5: Mean 77%"
          },
          {
            title: "exec(\"grade_batch(assignment='HW6')\")",
            state: "completed",
            description: "Graded HW6: Outlier detected in standard deviation bands."
          }
        ],
        statusPulse: {
          message: "Processing HW6 — running anomaly detection",
          elapsed: "11m 45s"
        },
        elicitation: {
          id: "int-audit-2",
          questions: [
            {
              id: "q1",
              title: "Student s_017 shows a sudden score drop in HW6 (84→31).",
              options: [
                { label: "Flag for follow-up", value: "flag" },
                { label: "Exclude from trend", value: "exclude" }
              ]
            }
          ]
        }
      }
    ]
  },
  {
    id: "student-code-debug",
    title: "Student: Code Debugging",
    description: "T7: Student needs help fixing a bug in their programming assignment. Agent uses sandbox execution.",
    messages: [
      {
        id: "scd1",
        role: "user",
        senderName: "Student",
        timestamp: "2:05 PM",
        content: "My sorting algorithm is failing on the autograder. Can you look at my code?",
        attachments: [
          {
            name: "mergesort.py",
            size: "2 KB",
            type: "Python"
          }
        ]
      },
      {
        id: "scd2",
        role: "assistant",
        senderName: "Teaching Agent",
        timestamp: "2:06 PM",
        content: "Your code looks close, but it's failing when the list contains duplicate numbers. What happens in your `merge` function when `left[i] == right[j]`?",
        tasks: [
          {
            title: "read_file(\"mergesort.py\")",
            state: "completed",
            description: "Read the provided python script."
          },
          {
            title: "exec(\"python -m venv sandbox\")",
            state: "completed",
            description: "Created safe execution sandbox environment."
          },
          {
            title: "exec(\"python -m unittest tests.test_mergesort\")",
            state: "completed",
            description: "Ran hidden test suite cs101_hw4. 8/10 passed, failed on array with duplicates."
          }
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
      },
      {
        id: "scd4",
        role: "assistant",
        senderName: "Teaching Agent",
        timestamp: "2:08 PM",
        content: "Exactly! How could you update your condition to handle duplicates correctly without losing elements?"
      }
    ]
  },
  {
    id: "ta-plagiarism-check",
    title: "TA: Plagiarism Check",
    description: "T8: Teaching Assistant running an integrity check on a midterm. Large batch processing, cross-referencing.",
    messages: [
      {
        id: "ta1",
        role: "user",
        senderName: "TA Mike",
        timestamp: "4:00 PM",
        content: "Run an integrity check on the CS201 Midterm submissions. Look for unusually high semantic similarity between code structures."
      },
      {
        id: "ta2",
        role: "assistant",
        senderName: "Integrity Checker",
        timestamp: "4:03 PM",
        content: "I have parsed 120 submissions and computed structural similarity scores across all 7,140 pairs using AST analysis. Most submissions look fine, but I have flagged 3 pairs with > 0.85 structural similarity [1].",
        tasks: [
          {
            title: "fetch_submissions(\"cs201_midterm\")",
            state: "completed",
            description: "Retrieved 120 submission files."
          },
          {
            title: "exec(\"python build_ast.py --batch cs201_midterm\")",
            state: "completed",
            description: "Generated Abstract Syntax Trees for all 120 files."
          },
          {
            title: "exec(\"python compute_ast_similarity.py\")",
            state: "completed",
            description: "Computed 7,140 pairwise similarity matrices using tree-edit distance."
          }
        ],
        statusPulse: {
          message: "Computing pairwise AST similarities — 4,200 of 7,140 pairs",
          elapsed: "2m 40s"
        },
        sources: [
          {
            index: 1,
            title: "Similarity Matrix Dataset",
            snippet: "Matrix containing pairwise structural similarity scores for all submissions.",
            type: "file"
          }
        ],
        elicitation: {
          id: "int-plagiarism",
          questions: [
            {
              id: "q1",
              title: "s_042 and s_089 share 92% AST structure on Q3. Flag them?",
              options: [
                { label: "Flag all 3 pairs", value: "flag" },
                { label: "Ignore", value: "ignore" },
                { label: "Let me review code side-by-side", value: "review" }
              ]
            }
          ]
        },
        canvasContent: {
          title: "Code Similarity Heatmap",
          type: "Python · Plotly",
          visualType: "chart",
          data: {
             regions: ["s_042", "s_089", "s_101", "s_034"],
             years: [1, 2, 3, 4],
             series: {
               "s_042": [1.0, 0.92, 0.1, 0.2],
               "s_089": [0.92, 1.0, 0.15, 0.1],
               "s_101": [0.1, 0.15, 1.0, 0.88],
               "s_034": [0.2, 0.1, 0.88, 1.0]
             }
          }
        }
      }
    ]
  },
  {
    id: "system-error-recovery",
    title: "System: Error & Recovery",
    description: "T9: Agent encounters an external system failure and recovers. Displays the error UI block.",
    messages: [
      {
        id: "sys1",
        role: "user",
        senderName: "Professor Allan",
        timestamp: "5:00 PM",
        content: "Sync the final grades for HW4 to the Canvas LMS."
      },
      {
        id: "sys2",
        role: "assistant",
        senderName: "LMS Integrator",
        timestamp: "5:01 PM",
        content: "I attempted to sync the grades, but the Canvas API timed out.",
        tasks: [
          {
            title: "read_file(\"hw4_grades.csv\")",
            state: "completed",
            description: "Loaded 45 student grade records."
          },
          {
            title: "exec(\"curl -X POST https://canvas.edu/api/v1/courses/...\")",
            state: "running",
            description: "Attempting to POST grades to Canvas API endpoint."
          },
          {
            title: "sync_lms_grades(\"hw4\", \"canvas\")",
            state: "failed",
            description: "HTTP 503 Service Unavailable: Canvas API timeout after 30s."
          }
        ],
        elicitation: {
          id: "int-error",
          questions: [
            {
              id: "q1",
              title: "Tool error: Canvas LMS sync failed. Retry now?",
              options: [
                { label: "Retry now", value: "retry" },
                { label: "Abort", value: "abort" }
              ]
            }
          ]
        }
      },
      {
        id: "sys3",
        role: "user",
        senderName: "Professor Allan",
        timestamp: "5:02 PM",
        content: "Retry now"
      },
      {
        id: "sys4",
        role: "assistant",
        senderName: "LMS Integrator",
        timestamp: "5:03 PM",
        content: "Grades synced successfully on the second attempt.",
        tasks: [
          {
            title: "sync_lms_grades(\"hw4\", \"canvas\")",
            state: "completed",
            description: "Success: 45 grades synced to Canvas (Status: 200 OK)."
          }
        ]
      }
    ]
  },
  {
    id: "scrolling-debug",
    title: "Vercel AI SDK Scroll Demo",
    description: "Demonstrates how the MessageScroller handles streaming auto-scroll pinning.",
    messages: [
      {
        id: "m1",
        role: "user",
        senderName: "Student Developer",
        timestamp: "7:24 PM",
        content: "I'm building a chat for our app and the scroll behavior is driving me nuts. Every time the AI streams a reply, the whole thread jumps around.",
      },
      {
        id: "m2",
        role: "assistant",
        senderName: "Fair Co-pilot",
        timestamp: "7:25 PM",
        content: "That's the classic streaming scroll problem. Wrap your message list in `MessageScroller` and turn on `autoScroll` — the viewport pins to the bottom as tokens arrive, so users always see the latest text land in place.\n\nThe important part: it only auto-scrolls while the reader is already at the bottom. The moment they scroll up to read something earlier, auto-scroll backs off and their position is preserved [1]. You get smooth streaming without fighting the user's intent [2].",
        tasks: [
          {
            title: "read_file(\"src/components/ui/chat/message-scroller.tsx\")",
            state: "completed",
            description: "Inspected scroll viewport event handlers."
          },
          {
            title: "write_file(\"src/components/ui/chat/message-scroller.tsx\")",
            state: "completed",
            description: "Fixed scroll anchoring constraints."
          }
        ],
        sources: [
          {
            index: 1,
            title: "Shadcn MessageScroller Docs",
            url: "https://ui.shadcn.com/docs/components/radix/message-scroller",
            snippet: "API reference and layout classes for implementing the message viewport scroll pinning.",
            type: "web"
          },
          {
            index: 2,
            title: "Vercel AI SDK Elements API",
            url: "https://elements.ai-sdk.dev/components/task",
            snippet: "Official library of status-aware UI components for building responsive agent chat flows.",
            type: "web"
          }
        ],
        canvasContent: {
          title: "MessageScroller Code Example",
          type: "React · TypeScript",
          visualType: "code",
          code: `import { MessageScroller } from "@shadcn/react/message-scroller";\n \nexport function ChatList({ messages }) {\n  return (\n    <MessageScroller.Provider autoScroll>\n      <MessageScroller.Root className="h-[500px]">\n        <MessageScroller.Viewport>\n          <MessageScroller.Content>\n            {messages.map((m) => (\n              <MessageScroller.Item key={m.id} messageId={m.id}>\n                <Bubble role={m.role}>{m.content}</Bubble>\n              </MessageScroller.Item>\n            ))}\n          </MessageScroller.Content>\n        </MessageScroller.Viewport>\n      </MessageScroller.Root>\n    </MessageScroller.Provider>\n  );\n}`
        }
      }
    ]
  },
  {
    id: "simulation",
    title: "Double Pendulum Simulation",
    description: "A physics simulation helping students visualize chaotic motion.",
    messages: [
      {
        id: "sim1",
        role: "user",
        senderName: "Physics Teacher",
        timestamp: "7:12 PM",
        content: "Can you create an interactive double pendulum simulation to help my students understand chaotic motion? I want them to be able to drag the pendulums to set the initial angles and watch the trajectory."
      },
      {
        id: "sim2",
        role: "assistant",
        senderName: "Physics Tutor",
        timestamp: "7:13 PM",
        content: "Sure! A double pendulum is a classic example of a simple physical system that exhibits chaotic behavior [1]. The motion is governed by a set of coupled ordinary differential equations.\n\nI will create a real-time interactive canvas simulation using the Runge-Kutta 4th order method to solve the equations of motion accurately.",
        tasks: [
          {
            title: "read_file(\"DoublePendulum.tsx\")",
            state: "completed",
            description: "Inspected existing physics canvas component properties."
          },
          {
            title: "write_file(\"src/components/physics/double-pendulum.tsx\")",
            state: "completed",
            description: "Implemented RK4 coordinate numerical integration loops."
          },
          {
            title: "exec(\"bun build --minify\")",
            state: "completed",
            description: "Bundled simulation assets cleanly."
          }
        ],
        sources: [
          {
            index: 1,
            title: "Double Pendulum Lagrangian Mechanics",
            url: "https://en.wikipedia.org/wiki/Double_pendulum",
            snippet: "Detailed equations of motion and chaos theory mathematics.",
            type: "web"
          }
        ],
        canvasContent: {
          title: "Double Pendulum Motion Solver",
          type: "HTML5 Canvas · JS",
          visualType: "simulation"
        }
      }
    ]
  }
]
