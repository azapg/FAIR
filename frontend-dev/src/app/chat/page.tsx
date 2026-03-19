import * as React from "react"
import { cn } from "@/lib/utils"
import {
    Chat,
    Conversation,
    Message,
    Reasoning,
    Widget,
    ChatInputContainer,
    ChatInput,
    ChatInputActions,
    Canva,
    CanvaTriggerCard,
    ChainOfThoughtStep
} from "@/components/chat"
import { Code, FileText, Image as ImageIcon, ChevronDown, Copy, CheckCircle2, FileCode2, ArrowUp, Paperclip, ListChecks, SquareDashed, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function ChatPage() {
    const [canvaOpen, setCanvaOpen] = React.useState(true)
    const [chatMessage, setChatMessage] = React.useState("")

    return (
        <div className="h-[calc(100vh-theme(spacing.16))] w-full flex overflow-hidden">
            <Chat>
                <Conversation>
                    <div className="flex items-center justify-between mb-8 px-2 md:px-0">
                        <h1 className="text-xl font-bold tracking-tight text-foreground">Plotting TB cases over time</h1>
                        <Button variant="ghost" size="icon">
                            ...
                        </Button>
                    </div>

                    <Message role="user">
                        <span className="text-[15px] leading-relaxed">
                            Can you create a plot of all TB cases over time per region? Also add a trend line
                        </span>
                    </Message>

                    <Message role="assistant">
                        <Reasoning summary="Analyzed the request and parsed local file">
                            <ChainOfThoughtStep
                                icon={FileText}
                                label="Analyzed user request for Plotting TB cases and identified attached CSV"
                            />
                            <ChainOfThoughtStep
                                icon={FileCode2}
                                label="Executed code to inspect CSV structure"
                                description={
                                    <div className="bg-muted px-2.5 py-1 rounded text-xs w-fit text-foreground mt-2 font-mono flex items-center gap-2 border shadow-xs">
                                        <div className="w-2.5 h-2.5 rounded-sm bg-[#fcd34d]"></div>
                                        import pandas as pd <span className="opacity-50"># Load the CSV file...</span>
                                    </div>
                                }
                            />
                            <ChainOfThoughtStep
                                icon={CheckCircle2}
                                label="Ready to summarize Data Analysis"
                            />
                        </Reasoning>

                        <p className="mb-4 mt-2 text-[15px] text-foreground/90 font-medium tracking-tight">
                            Before proceeding with creating the plot, I need to analyze the attached CSV file to understand its structure, columns, and data types. This will ensure I can accurately process the data for TB cases over time per region.
                        </p>
                        <p className="text-[15px] text-foreground/90 font-medium tracking-tight">
                            I have successfully loaded the CSV file. The columns include 'Year', 'Region', 'TB Cases', etc. Now I can use pandas to group by region and year, and use plotly to chart it.
                        </p>
                    </Message>

                    <Message role="assistant">
                        <h3 className="font-semibold text-[17px] block mb-3 text-foreground tracking-tight">Summary of Data Analysis</h3>
                        <p className="mb-4 text-[15px] text-foreground/80 leading-relaxed font-medium">
                            I've analyzed the attached CSV file ("TB Burden Country Data.csv") by loading it into a Pandas DataFrame. The file contains data on tuberculosis (TB) burden across various countries and regions from 1990 onwards. Key observations from the first few rows and DataFrame summary:
                        </p>
                        <ul className="list-disc pl-5 space-y-3 mt-4 text-[15px] text-foreground/80 font-medium marker:text-muted-foreground">
                            <li><strong className="text-foreground">Structure:</strong> The dataset has 5,120 rows and 47 columns, including details like country names, ISO codes, region, year, estimated TB incidence, prevalence, and mortality.</li>
                        </ul>
                        <CanvaTriggerCard
                            icon={<Code className="w-5 h-5 opacity-70" />}
                            title="Claude thinking component"
                            type="Code · HTML"
                            actionText="Download"
                            onClick={() => setCanvaOpen(true)}
                        />
                    </Message>

                    <ChatInputContainer>
                        <ChatInput
                            value={chatMessage}
                            onChange={(e) => setChatMessage(e.target.value)}
                        />
                        <ChatInputActions>
                            <Button variant="ghost" size="icon">
                                <Plus className="w-4 h-4" />
                            </Button>
                            <div className="flex items-center gap-3 pr-1 shrink-0">
                                <Button variant="ghost">
                                    Sonnet 4.6 <ChevronDown className="w-4 h-4 opacity-70" />
                                </Button>

                                <Button
                                    className={cn(
                                        "p-2 rounded-full transition-all flex items-center justify-center shadow-sm focus:outline-none focus:ring-2 focus:ring-ring shrink-0",
                                        chatMessage.trim().length > 0
                                            ? "bg-foreground text-background hover:opacity-90 cursor-pointer"
                                            : "bg-muted text-muted-foreground cursor-not-allowed opacity-50"
                                    )}
                                    disabled={chatMessage.trim().length === 0}
                                >
                                    <ArrowUp className="w-4 h-4 stroke-[3]" />
                                </Button>
                            </div>
                        </ChatInputActions>
                    </ChatInputContainer>
                </Conversation>

                <Canva
                    isOpen={canvaOpen}
                    onClose={() => setCanvaOpen(false)}
                    title={
                        <div className="flex gap-1.5 sm:gap-2 items-center bg-muted/40 p-1 rounded-full border border-border/50 shadow-sm relative right-2">
                            <Button className="flex items-center justify-center gap-1.5 h-7 px-3 sm:px-4 rounded-full bg-transparent text-muted-foreground hover:text-foreground hover:bg-muted/80 transition-all text-xs font-semibold active:scale-95 duration-100 ease-out cursor-pointer group">
                                <FileText className="w-3.5 h-3.5 group-hover:-translate-y-[1px] transition-transform opacity-70" />
                                <span className="hidden sm:inline">Report</span>
                            </Button>
                            <Button className="flex items-center justify-center gap-1.5 h-7 px-3 sm:px-4 rounded-full bg-background shadow-xs border border-border/80 text-foreground font-semibold text-xs transition-all active:scale-95 duration-100 ease-out cursor-pointer group">
                                <Code className="w-3.5 h-3.5 text-foreground/70 group-hover:scale-105 transition-transform" />
                                <span className="hidden sm:inline">Code output</span>
                                <ChevronDown className="w-3.5 h-3.5 text-muted-foreground/70 ml-0.5 group-hover:translate-y-[1px] transition-transform" />
                            </Button>
                        </div>
                    }
                >
                    <div className="p-3 sm:p-5 h-full space-y-6 flex flex-col items-stretch max-w-full">
                        <div className="p-5 bg-background border rounded-2xl shadow-sm">
                            <div className="flex items-center pb-3 border-b justify-between mb-5">
                                <div className="flex items-center gap-2 text-sm font-bold text-foreground tracking-tight">
                                    <div className="w-2.5 h-2.5 rounded-sm bg-[#fcd34d]"></div> Python
                                </div>
                                <Button className="text-muted-foreground hover:text-foreground transition-colors p-1.5 hover:bg-muted rounded text-xs px-2 flex items-center gap-1 focus:outline-none focus:ring-2 focus:ring-ring">
                                    <Copy className="w-3.5 h-3.5" />
                                </Button>
                            </div>
                            <pre className="text-[13px] text-muted-foreground font-mono space-y-1.5 overflow-x-auto pb-4 custom-scrollbar whitespace-pre">
                                <code className="text-foreground/80"><span className="text-[#c678dd]">import</span> <span className="text-[#61afef]">pandas</span> <span className="text-[#c678dd]">as</span> <span className="text-[#d19a66]">pd</span></code><br />
                                <code className="text-foreground/80"><span className="text-[#c678dd]">import</span> <span className="text-[#61afef]">plotly.express</span> <span className="text-[#c678dd]">as</span> <span className="text-[#d19a66]">px</span></code><br />
                                <code className="text-foreground/80"><span className="text-[#c678dd]">import</span> <span className="text-[#61afef]">plotly.graph_objects</span> <span className="text-[#c678dd]">as</span> <span className="text-[#d19a66]">go</span></code><br />
                                <code className="text-foreground/80"><span className="text-[#c678dd]">from</span> <span className="text-[#61afef]">scipy.stats</span> <span className="text-[#c678dd]">import</span> <span className="text-[#56b6c2]">linregress</span></code><br />
                                <code className="text-foreground/80"><span className="text-[#c678dd]">import</span> <span className="text-[#61afef]">numpy</span> <span className="text-[#c678dd]">as</span> <span className="text-[#d19a66]">np</span></code><br />
                                <code className="text-foreground/80"><span className="text-[#c678dd]">import</span> <span className="text-[#61afef]">os</span></code><br />
                                <br />
                                <code className="text-muted-foreground/50 italic"># Ensure the /files directory exists</code><br />
                                <code className="text-foreground/80"><span className="text-[#e5c07b]">os.makedirs</span>(<span className="text-[#98c379]">'/files'</span>, exist_ok=<span className="text-[#d19a66]">True</span>)</code>
                            </pre>
                            <div className="pt-3 border-t text-center flex items-center justify-center -mb-2 mt-2">
                                <Button className="text-[11px] font-semibold text-muted-foreground hover:text-foreground transition-colors flex items-center justify-center gap-1 w-auto bg-muted/30 hover:bg-muted/50 px-3 py-1.5 rounded-full">
                                    Show all code <ChevronDown className="w-3.5 h-3.5" />
                                </Button>
                            </div>
                        </div>

                        <div className="bg-background border rounded-2xl shadow-sm overflow-hidden flex flex-col min-h-0 shrink-0">
                            <div className="flex items-center gap-4 sm:gap-6 text-[13px] font-semibold border-b pt-3 px-5 whitespace-nowrap overflow-x-auto text-muted-foreground custom-scrollbar scrollbar-hide">
                                <Button className="flex items-center gap-1.5 text-foreground border-b-[2px] border-foreground pb-2 -mb-[2px] transition-colors focus:outline-none">
                                    <span className="font-mono text-muted-foreground opacity-70 leading-none mb-[2px]">{">_"}</span> Output · <span className="bg-muted px-1.5 py-0.5 rounded-[4px] text-[11px] border shadow-xs text-muted-foreground">0</span>
                                </Button>
                                <Button className="flex items-center gap-1.5 hover:text-foreground pb-2 -mb-[2px] transition-colors focus:outline-none">
                                    <ImageIcon className="w-3.5 h-3.5 opacity-70" /> Images · <span className="bg-muted px-1.5 py-0.5 rounded-[4px] text-[11px] border shadow-xs text-muted-foreground">0</span>
                                </Button>
                                <Button className="flex items-center gap-1.5 hover:text-foreground pb-2 -mb-[2px] transition-colors focus:outline-none">
                                    <FileText className="w-3.5 h-3.5 opacity-70" /> Files · <span className="bg-muted px-1.5 py-0.5 rounded-[4px] text-[11px] border shadow-xs text-muted-foreground">0</span>
                                </Button>
                                <Button className="flex items-center gap-1.5 hover:text-foreground pb-2 -mb-[2px] transition-colors focus:outline-none">
                                    <span className="opacity-70">Other</span> · <span className="bg-muted px-1.5 py-0.5 rounded-[4px] text-[11px] border shadow-xs text-foreground font-bold">1</span>
                                </Button>
                                <Button className="flex items-center gap-1.5 hover:text-foreground pb-2 -mb-[2px] transition-colors focus:outline-none">
                                    <span className="opacity-70">Errors</span> · <span className="bg-muted px-1.5 py-0.5 rounded-[4px] text-[11px] border shadow-xs text-muted-foreground">0</span>
                                </Button>
                            </div>

                            <div className="p-5 sm:p-7 pb-8 pt-6">
                                <h4 className="font-bold text-center mb-8 text-[15px] tracking-tight text-foreground/90">TB Cases Over Time by Region</h4>
                                <div className="aspect-[1.5] w-full bg-transparent border-l border-b border-muted-foreground/30 flex flex-col pt-4 pr-16 pb-6 pl-3 relative group hover:border-muted-foreground transition-colors selection-transparent select-none">
                                    {/* Y axis labels */}
                                    <div className="absolute -left-8 top-[10%] text-[10px] text-muted-foreground font-medium w-6 text-right">3.5M</div>
                                    <div className="absolute -left-8 top-[30%] text-[10px] text-muted-foreground font-medium w-6 text-right">3M</div>
                                    <div className="absolute -left-8 top-[50%] text-[10px] text-muted-foreground font-medium w-6 text-right">2.5M</div>
                                    <div className="absolute -left-8 top-[70%] text-[10px] text-muted-foreground font-medium w-6 text-right">2M</div>

                                    {/* Y axis title */}
                                    <div className="absolute -left-16 top-1/2 -translate-y-1/2 -rotate-90 text-[11px] font-semibold text-muted-foreground whitespace-nowrap tracking-wide">Estimated Incident TB Cases</div>

                                    {/* X axis lines / Grid */}
                                    <div className="absolute left-0 right-16 top-[10%] border-t border-dashed border-border/60"></div>
                                    <div className="absolute left-0 right-16 top-[30%] border-t border-dashed border-border/60"></div>
                                    <div className="absolute left-0 right-16 top-[50%] border-t border-dashed border-border/60"></div>
                                    <div className="absolute left-0 right-16 top-[70%] border-t border-dashed border-border/60"></div>
                                    <div className="absolute left-0 right-16 top-[90%] border-t border-dashed border-border/60"></div>

                                    {/* X axis labels */}
                                    <div className="absolute -bottom-6 left-[10%] text-[10px] text-muted-foreground font-medium -translate-x-1/2">1990</div>
                                    <div className="absolute -bottom-6 left-[30%] text-[10px] text-muted-foreground font-medium -translate-x-1/2">1995</div>
                                    <div className="absolute -bottom-6 left-[50%] text-[10px] text-muted-foreground font-medium -translate-x-1/2">2000</div>
                                    <div className="absolute -bottom-6 left-[70%] text-[10px] text-muted-foreground font-medium -translate-x-1/2">2005</div>
                                    <div className="absolute -bottom-6 left-[90%] text-[10px] text-muted-foreground font-medium -translate-x-1/2">2010</div>

                                    {/* X axis title */}
                                    <div className="absolute -bottom-10 left-[45%] text-[11px] font-semibold text-muted-foreground tracking-wide">Year</div>

                                    {/* Lines simulation Using SVG */}
                                    <svg className="absolute inset-x-0 inset-y-0 w-[calc(100%-4rem)] h-full overflow-visible" preserveAspectRatio="none">
                                        {/* Trend lines (dashed) */}
                                        <path d="M 0,10 Q 50,20 100,5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeDasharray="5 5" className="text-blue-500/60" vectorEffect="non-scaling-stroke" />
                                        <path d="M 0,30 Q 50,45 100,20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeDasharray="5 5" className="text-orange-500/60" vectorEffect="non-scaling-stroke" />
                                        <path d="M 0,60 Q 50,75 100,80" fill="none" stroke="currentColor" strokeWidth="1.5" strokeDasharray="5 5" className="text-pink-500/60" vectorEffect="non-scaling-stroke" />
                                        <path d="M 0,72 Q 50,75 100,77" fill="none" stroke="currentColor" strokeWidth="1.5" strokeDasharray="5 5" className="text-purple-500/60" vectorEffect="non-scaling-stroke" />
                                        <path d="M 0,82 Q 50,85 100,89" fill="none" stroke="currentColor" strokeWidth="1.5" strokeDasharray="5 5" className="text-green-500/60" vectorEffect="non-scaling-stroke" />
                                        <path d="M 0,92 Q 50,95 100,99" fill="none" stroke="currentColor" strokeWidth="1.5" strokeDasharray="5 5" className="text-cyan-500/60" vectorEffect="non-scaling-stroke" />

                                        {/* Actual lines (solid) */}
                                        <path d="M 0,85 L 10,75 L 20,70 L 30,60 L 40,55 L 50,45 L 60,40 L 70,35 L 80,35 L 90,40 L 100,45" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-blue-500" vectorEffect="non-scaling-stroke" />
                                        <path d="M 0,20 L 10,25 L 20,15 L 30,5 L 40,0 L 50,-5 L 60,-10 L 70,0 L 80,5 L 90,10 L 100,15" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-orange-500" vectorEffect="non-scaling-stroke" />
                                        <path d="M 0,50 L 10,55 L 20,50 L 30,55 L 40,60 L 50,55 L 60,65 L 70,60 L 80,65 L 90,70 L 100,75" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-pink-500" vectorEffect="non-scaling-stroke" />
                                        <path d="M 0,75 L 20,72 L 40,70 L 60,78 L 80,72 L 100,82" fill="none" stroke="#a855f7" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
                                        <path d="M 0,80 L 20,83 L 40,79 L 60,86 L 80,83 L 100,88" fill="none" stroke="#22c55e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
                                        <path d="M 0,85 L 20,88 L 40,89 L 60,93 L 80,95 L 100,98" fill="none" stroke="#06b6d4" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />

                                    </svg>

                                    {/* Legend */}
                                    <div className="absolute -right-2 top-0 w-16 text-[10px] space-y-2 flex flex-col justify-start items-start text-muted-foreground font-semibold p-1 rounded-sm">
                                        <span className="font-bold text-foreground text-xs mb-1 tracking-tight">Region</span>
                                        <div className="flex items-center gap-1.5 opacity-90 transition-opacity"><div className="w-2.5 h-0.5 bg-blue-500"></div>AFR</div>
                                        <div className="flex items-center gap-1.5 opacity-90 transition-opacity"><div className="w-2.5 h-0.5 bg-orange-500"></div>AMR</div>
                                        <div className="flex items-center gap-1.5 opacity-90 transition-opacity"><div className="w-2.5 h-0.5 bg-pink-500"></div>EMR</div>
                                        <div className="flex items-center gap-1.5 opacity-90 transition-opacity"><div className="w-2.5 h-0.5 bg-purple-500"></div>EUR</div>
                                        <div className="flex items-center gap-1.5 opacity-90 transition-opacity"><div className="w-2.5 h-0.5 bg-green-500"></div>SEA</div>
                                        <div className="flex items-center gap-1.5 opacity-90 transition-opacity"><div className="w-2.5 h-0.5 bg-cyan-500"></div>WPR</div>

                                        <div className="flex items-center gap-1.5 opacity-70 transition-opacity mt-4"><div className="w-2.5 border-t-[1.5px] border-dashed border-blue-500/60"></div>AFR <br />Trend</div>
                                        <div className="flex items-center gap-1.5 opacity-70 transition-opacity"><div className="w-2.5 border-t-[1.5px] border-dashed border-orange-500/60"></div>AMR <br />Trend</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </Canva>
            </Chat>
        </div>
    )
}
