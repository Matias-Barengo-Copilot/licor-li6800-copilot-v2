import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/auth";
import { getAttendanceRows, getSessionTrendRows, getPrograms } from "@/lib/db";
import {
  overviewMetrics,
  studentPerformanceTable,
  teamPerformance,
  atRiskStudents,
} from "@/lib/analytics";
import { loadWork } from "@/lib/data-loader";
import { formatProgram } from "@/lib/format-program";
import OpenAI from "openai";

// ─── System prompt builder ────────────────────────────────────────────────────

async function buildSystemPrompt(): Promise<string> {
  const [att, session, rawPrograms, work] = await Promise.all([
    getAttendanceRows(),
    getSessionTrendRows(),
    getPrograms(),
    Promise.resolve(loadWork()),
  ]);

  const perf = studentPerformanceTable(att, work);
  const metrics = overviewMetrics(att, session);
  const teams = teamPerformance(perf);
  const atRisk = atRiskStudents(perf);
  const programs = rawPrograms.map(formatProgram);

  const teamSummary = teams
    .map(
      (t) =>
        `  - ${t["Project Team Name"]}: ${t.Students} students, ` +
        `${t.Avg_Attendance.toFixed(1)}% attendance, ` +
        `${t.Avg_Good != null ? t.Avg_Good.toFixed(1) : "—"}% work quality`
    )
    .join("\n");

  const atRiskNames = atRisk
    .slice(0, 8)
    .map(
      (r) =>
        `  - ${r["First Name"]} ${r["Last Name"]}: ` +
        `${r["Attendance %"].toFixed(1)}% attendance, Priority=${r.Priority}`
    )
    .join("\n");

  const programsSummary = programs
    .map((p) => {
      const rate =
        p.attendance_rate != null
          ? `${p.attendance_rate.toFixed(1)}%`
          : "no sessions yet";
      return (
        `  - ${p.icon} ${p.name} (${p.site ?? ""}): ` +
        `${p.enrolled} students enrolled, ${p.session_count} sessions, ` +
        `attendance ${rate}`
      );
    })
    .join("\n");

  return `You are an expert education data analyst assistant for Urban Arts, a NYC youth arts program.
You have access to real program data from the live database.

LIVE DATA SUMMARY (all programs):
- Total students tracked: ${metrics.total_students}
- Average attendance across all sessions: ${metrics.avg_attendance.toFixed(1)}%
- Total sessions recorded: ${metrics.sessions}
- High performers (≥90% attendance): ${metrics.high_performers}
- Students needing attention (<70%): ${metrics.low_performers}
- Critical (<50% attendance): ${metrics.critical_students}

ACTIVE PROGRAMS:
${programsSummary || "  (no programs found)"}

PROJECT TEAMS:
${teamSummary || "  (no team data)"}

AT-RISK STUDENTS:
${atRiskNames || "  (none flagged)"}

STUDENT DEMOGRAPHICS (SY2023-24 actuals / 2024-25 projected):
- Race: 36% Hispanic/Latinx, 29% Asian, 25% Black/African-American, 9% White
- Gender: 62% Man/Boy, 34% Woman/Girl, 4% Non-Binary
- 7% of students have a documented disability
- Income: 42% from households earning <$50k/yr; 67% from households <$75k/yr
- Locations: 38% Brooklyn, 24% Bronx, 20% Queens, 14% Manhattan
- Grades: 35% 9th, 30% 10th, 22% 11th, 13% 12th

Your role:
- Answer questions about attendance patterns, student performance, and program trends
- Provide actionable insights for program staff (not just statistics)
- Flag specific at-risk students when asked
- Suggest interventions based on data patterns
- Be concise, specific, and use actual numbers from the data above

Keep responses focused and under 250 words unless asked for detail.`;
}

// ─── Chart tool definition ────────────────────────────────────────────────────

const CHART_TOOL: OpenAI.Chat.Completions.ChatCompletionTool = {
  type: "function",
  function: {
    name: "show_chart",
    description:
      "Display a visual chart or graph directly in the chat. " +
      "Use this whenever the user asks for a graph, chart, or visualization, " +
      "or when displaying data visually would be clearer than listing numbers.",
    parameters: {
      type: "object",
      properties: {
        chart_type: {
          type: "string",
          enum: ["pie", "donut", "bar", "horizontal_bar", "line"],
        },
        title: { type: "string" },
        data: {
          type: "array",
          items: {
            type: "object",
            properties: {
              label: { type: "string" },
              value: { type: "number" },
            },
            required: ["label", "value"],
          },
        },
        unit: { type: "string", default: "%" },
        insight: { type: "string" },
      },
      required: ["chart_type", "title", "data"],
    },
  },
};

// ─── Route ────────────────────────────────────────────────────────────────────

export async function POST(req: NextRequest) {
  const auth = requireAuth(req);
  if (auth instanceof NextResponse) return auth;

  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    return NextResponse.json(
      { detail: "OPENAI_API_KEY not configured" },
      { status: 400 }
    );
  }

  let body: { messages: Array<{ role: string; content: string }> };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body" }, { status: 400 });
  }

  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      const enqueue = (data: object) => {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify(data)}\n\n`)
        );
      };

      try {
        const systemPrompt = await buildSystemPrompt();
        const client = new OpenAI({ apiKey });

        const messages: OpenAI.Chat.Completions.ChatCompletionMessageParam[] =
          [
            { role: "system", content: systemPrompt },
            ...body.messages.map((m) => ({
              role: m.role as "user" | "assistant",
              content: m.content,
            })),
          ];

        const openaiStream = await client.chat.completions.create({
          model: "gpt-4o",
          messages,
          tools: [CHART_TOOL],
          tool_choice: "auto",
          max_tokens: 800,
          temperature: 0.3,
          stream: true,
        });

        const toolCallsAcc: Record<
          number,
          { id: string; name: string; arguments: string }
        > = {};
        let finishReason: string | null = null;

        for await (const chunk of openaiStream) {
          const choice = chunk.choices[0];
          finishReason = choice.finish_reason;

          if (choice.delta.content) {
            enqueue({ content: choice.delta.content });
          }

          if (choice.delta.tool_calls) {
            for (const tc of choice.delta.tool_calls) {
              const idx = tc.index;
              if (!toolCallsAcc[idx]) {
                toolCallsAcc[idx] = {
                  id: tc.id ?? "",
                  name: tc.function?.name ?? "",
                  arguments: "",
                };
              }
              if (tc.id) toolCallsAcc[idx].id = tc.id;
              if (tc.function?.name) toolCallsAcc[idx].name = tc.function.name;
              if (tc.function?.arguments)
                toolCallsAcc[idx].arguments += tc.function.arguments;
            }
          }
        }

        if (finishReason === "tool_calls") {
          for (const tc of Object.values(toolCallsAcc)) {
            if (tc.name === "show_chart") {
              try {
                const args = JSON.parse(tc.arguments);
                enqueue({ type: "chart", chart: args });

                const followupMessages: OpenAI.Chat.Completions.ChatCompletionMessageParam[] =
                  [
                    ...messages,
                    {
                      role: "assistant",
                      tool_calls: [
                        {
                          id: tc.id,
                          type: "function" as const,
                          function: {
                            name: "show_chart",
                            arguments: tc.arguments,
                          },
                        },
                      ],
                    },
                    {
                      role: "tool",
                      tool_call_id: tc.id,
                      content: "Chart rendered successfully.",
                    },
                  ];

                const followup = await client.chat.completions.create({
                  model: "gpt-4o",
                  messages: followupMessages,
                  max_tokens: 200,
                  temperature: 0.3,
                });

                const comment = followup.choices[0].message.content;
                if (comment) enqueue({ content: comment });
              } catch {
                // JSON parse error in tool call args — skip
              }
            }
          }
        }

        enqueue("[DONE]" as unknown as object);
        // Actually send the [DONE] as a raw string SSE
        controller.enqueue(encoder.encode("data: [DONE]\n\n"));
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Unknown error";
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ error: msg })}\n\n`)
        );
      } finally {
        controller.close();
      }
    },
  });

  return new NextResponse(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
