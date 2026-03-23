"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Users, Clock, CheckCircle, Mail, LogOut, RefreshCw,
  ChevronRight, Eye, Edit3, Send, Download, Loader2,
  X, Save, AlertCircle, FileText, File, MessageCircle,
  SendHorizonal, Bot, BookOpen
} from "lucide-react";
import toast from "react-hot-toast";
import { adminApi } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Stats { total_clients: number; pending_review: number; approved: number; sent_to_client: number; }
interface Client {
  id: number; full_name: string; age: number; gender: string;
  goal: string; email: string; created_at: string;
  plan_status: string | null; plan_id: number | null;
}
interface ChatSession { revision: number; instructions: string[]; timestamp: string; }
interface Plan {
  id: number; submission_id: number; status: string;
  generated_plan: string | null; final_plan: string | null;
  admin_notes: string | null; rag_sources: string[];
  generation_progress: number; generation_stage: string | null;
  word_path: string | null;
  created_at: string; updated_at: string;
  regeneration_count: number;
  admin_chat_history: ChatSession[];
}
interface ClientDetail {
  full_name: string; age: number; gender: string; height_cm: number; weight_kg: number;
  goal: string; bmr: number; tdee: number; calorie_target: number;
  protein_target_g: number; carb_target_g: number; fat_target_g: number;
  medical_conditions: string[]; food_allergies: string[];
  diet_type: string; activity_level: string; exercise_preference: string[]; email: string; phone: string;
  city: string; state: string; target_weight_kg: number; timeline: string;
}

// ─── Status badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string | null }) {
  const map: Record<string, { color: string; label: string; icon: string }> = {
    generating: { color: "bg-blue-100 text-blue-800", label: "Generating...", icon: "⚙️" },
    pending: { color: "bg-yellow-100 text-yellow-800", label: "Pending Review", icon: "⏳" },
    failed: { color: "bg-red-100 text-red-800", label: "Generation Failed", icon: "❌" },
    approved: { color: "bg-green-100 text-green-800", label: "Approved", icon: "✅" },
    edited: { color: "bg-blue-100 text-blue-800", label: "Edited & Approved", icon: "✏️" },
    sent: { color: "bg-purple-100 text-purple-800", label: "Sent to Client", icon: "📧" },
    completed: { color: "bg-gray-100 text-gray-700", label: "Completed", icon: "🏁" },
  };
  const s = map[status || ""] || { color: "bg-gray-100 text-gray-500", label: "No plan yet", icon: "⌛" };
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${s.color}`}>
      {s.icon} {s.label}
    </span>
  );
}

// ─── Plan Viewer / Editor ─────────────────────────────────────────────────────

function PlanPanel({
  client, plan, chatMessages, onClose, onRefresh
}: {
  client: Client; plan: Plan | null;
  chatMessages: ChatMsg[];
  onClose: () => void; onRefresh: () => void;
}) {
  const [editMode, setEditMode] = useState(false);
  const [editedPlan, setEditedPlan] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<ClientDetail | null>(null);
  const [activeTab, setActiveTab] = useState<"plan" | "profile">("plan");
  const [liveProgress, setLiveProgress] = useState<{ pct: number; stage: string | null }>({ pct: 0, stage: null });

  useEffect(() => {
    if (plan) {
      setEditedPlan(plan.final_plan || plan.generated_plan || "");
      setNotes(plan.admin_notes || "");
      setLiveProgress({ pct: plan.generation_progress || 0, stage: plan.generation_stage || null });
    }
    adminApi.getClientDetail(client.id).then(r => setDetail(r.data)).catch(() => {});
  }, [plan, client.id]);

  // Auto-poll every 3 seconds while plan is generating
  useEffect(() => {
    if (!plan || plan.status !== "generating") return;
    const interval = setInterval(async () => {
      try {
        const res = await adminApi.getPlan(plan.id);
        const updated: Plan = res.data;
        // Update the plan in the parent via onRefresh when done
        if (updated.status !== "generating") {
          onRefresh();
          clearInterval(interval);
        } else {
          // Update progress in local state by triggering a plan prop re-render
          // We use a workaround: store live progress in local state
          setLiveProgress({ pct: updated.generation_progress, stage: updated.generation_stage });
        }
      } catch { /* ignore poll errors */ }
    }, 3000);
    return () => clearInterval(interval);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [plan?.id, plan?.status]);

  const planText = plan?.final_plan || plan?.generated_plan || "";

  const handleSave = async () => {
    if (!plan) return;
    setLoading(true);
    try {
      await adminApi.updatePlan(plan.id, { final_plan: editedPlan, admin_notes: notes });
      toast.success("Plan saved!");
      setEditMode(false);
      onRefresh();
    } catch { toast.error("Save failed"); }
    finally { setLoading(false); }
  };

  const handleApprove = async () => {
    if (!plan) return;
    setLoading(true);
    try {
      if (editMode && editedPlan !== planText) {
        await adminApi.updatePlan(plan.id, { final_plan: editedPlan, admin_notes: notes });
      }
      await adminApi.approvePlan(plan.id);
      toast.success("Plan approved! PDF is being generated...");
      setEditMode(false);
      onRefresh();
    } catch { toast.error("Approval failed"); }
    finally { setLoading(false); }
  };

  const handleSendEmail = async () => {
    if (!plan) return;
    if (!client.email) { toast.error("Client has no email address"); return; }
    setLoading(true);
    try {
      await adminApi.sendEmail(plan.id);
      toast.success(`Email sent to ${client.email}`);
      onRefresh();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      toast.error(e?.response?.data?.detail || "Email failed");
    }
    finally { setLoading(false); }
  };

  const handleDownload = async (url: string, filename: string) => {
    const token = localStorage.getItem("nutriveda_admin_token");
    try {
      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) { toast.error("Download failed — " + res.status); return; }
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(a.href);
    } catch { toast.error("Download failed"); }
  };

  const handleRegenerate = async () => {
    if (!plan) return;
    const userMsgs = chatMessages.filter(m => m.role === "user").map(m => m.content);
    const revNum = (plan.regeneration_count || 0) + 1;

    const confirmMsg = userMsgs.length > 0
      ? `Regenerate plan (Revision ${revNum}) with ${userMsgs.length} new instruction(s)?\n\n${userMsgs.map(m => `• ${m}`).join("\n").slice(0, 300)}${userMsgs.join("").length > 300 ? "\n..." : ""}`
      : "Regenerate plan? This will overwrite the current AI draft.";

    if (!confirm(confirmMsg)) return;
    setLoading(true);
    try {
      await adminApi.regeneratePlan(plan.id, undefined, userMsgs.length > 0 ? userMsgs : undefined);
      toast.success(userMsgs.length > 0
        ? `Revision ${revNum} started with ${userMsgs.length} instruction(s)...`
        : "Regenerating plan in background...");
      onRefresh();
    } catch { toast.error("Regeneration failed"); }
    finally { setLoading(false); }
  };

  const goalMap: Record<string, string> = {
    lose_weight: "Weight Loss", gain_muscle: "Muscle Gain",
    gain_muscle_lose_fat: "Gain Muscle & Lose Fat",
    maintain: "Maintenance", improve_health: "Health Improvement",
    medical_management: "Medical Management", sports_nutrition: "Sports Nutrition"
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-start justify-end">
      <motion.div
        initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
        transition={{ type: "spring", damping: 30, stiffness: 300 }}
        className="bg-white h-full w-full max-w-3xl flex flex-col shadow-2xl"
      >
        {/* Header */}
        <div className="p-5 border-b border-gray-100 flex items-center justify-between bg-green-600 text-white">
          <div>
            <h2 className="font-bold text-lg">{client.full_name}</h2>
            <p className="text-green-100 text-sm">
              {goalMap[client.goal] || client.goal} • {client.email || "No email"}
            </p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/20 rounded-lg transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-100 bg-gray-50">
          {[{ id: "plan", label: "Diet Plan", icon: "📋" }, { id: "profile", label: "Client Profile", icon: "👤" }].map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id as "plan" | "profile")}
              className={`flex-1 py-3 text-sm font-semibold transition-colors flex items-center justify-center gap-2 ${
                activeTab === t.id ? "text-green-700 border-b-2 border-green-600 bg-white" : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === "plan" && (
            <div className="p-5">
              {/* Status & sources */}
              {plan && (
                <div className="mb-4 flex items-center gap-3 flex-wrap">
                  <StatusBadge status={plan.status} />
                  {(plan.regeneration_count || 0) > 0 && (
                    <span className="text-xs bg-orange-50 text-orange-700 border border-orange-200 px-2 py-0.5 rounded-full font-semibold">
                      🔄 Revised ×{plan.regeneration_count}
                    </span>
                  )}
                  {plan.rag_sources?.length > 0 && (
                    <span className="text-xs text-gray-500">
                      📚 Sources: {plan.rag_sources.slice(0, 3).join(", ")}
                      {plan.rag_sources.length > 3 && ` +${plan.rag_sources.length - 3} more`}
                    </span>
                  )}
                </div>
              )}

              {/* Revision history */}
              {plan && (plan.admin_chat_history?.length || 0) > 0 && (
                <RevisionHistory history={plan.admin_chat_history} />
              )}

              {/* Admin notes */}
              <div className="mb-4">
                <label className="text-xs font-bold text-gray-600 block mb-1">Your Notes to Client</label>
                <textarea
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                  rows={2}
                  placeholder="Add a personal note for the client (optional)..."
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:border-green-500 focus:ring-1 focus:ring-green-100 outline-none text-sm resize-none"
                />
              </div>

              {/* Plan content */}
              {!plan ? (
                <div className="flex items-center gap-3 text-yellow-700 bg-yellow-50 border border-yellow-200 rounded-xl p-4">
                  <AlertCircle className="w-5 h-5 shrink-0" />
                  <span className="text-sm">No plan exists for this client yet.</span>
                </div>
              ) : plan.status === "generating" ? (
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 space-y-3">
                  <div className="flex items-center gap-3 text-blue-700">
                    <Loader2 className="w-5 h-5 animate-spin shrink-0" />
                    <span className="text-sm font-semibold">Generating your plan...</span>
                    <span className="ml-auto text-lg font-bold text-blue-800">{liveProgress.pct}%</span>
                  </div>
                  {/* Progress bar */}
                  <div className="w-full bg-blue-100 rounded-full h-3 overflow-hidden">
                    <motion.div
                      className="h-3 rounded-full bg-gradient-to-r from-blue-500 to-green-500"
                      initial={{ width: 0 }}
                      animate={{ width: `${liveProgress.pct}%` }}
                      transition={{ duration: 0.6, ease: "easeOut" }}
                    />
                  </div>
                  {/* Stage label */}
                  <p className="text-xs text-blue-600 font-medium">
                    {liveProgress.stage || "Starting generation..."}
                  </p>
                  {/* Stage milestones */}
                  <div className="flex justify-between text-xs text-blue-400 pt-1">
                    {[
                      { pct: 12, label: "Knowledge base" },
                      { pct: 18, label: "Building plan" },
                      { pct: 55, label: "Weeks 1–2" },
                      { pct: 92, label: "Weeks 3–4" },
                      { pct: 100, label: "Done!" },
                    ].map(m => (
                      <span key={m.label} className={liveProgress.pct >= m.pct ? "text-blue-600 font-semibold" : ""}>
                        {m.label}
                      </span>
                    ))}
                  </div>
                  <p className="text-xs text-gray-400">Auto-refreshing every 3 seconds</p>
                </div>
              ) : plan.status === "failed" ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-3 text-red-700 bg-red-50 border border-red-200 rounded-xl p-4">
                    <AlertCircle className="w-5 h-5 shrink-0" />
                    <div>
                      <div className="text-sm font-semibold">Plan generation failed</div>
                      <div className="text-xs mt-1 text-red-600">{plan.admin_notes || "Unknown error"}</div>
                    </div>
                  </div>
                  <button onClick={handleRegenerate}
                    className="w-full bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold py-2 px-4 rounded-xl transition-all">
                    Retry Generation
                  </button>
                </div>
              ) : plan.status === "pending" && !plan.generated_plan ? (
                <div className="flex items-center gap-3 text-blue-700 bg-blue-50 border border-blue-200 rounded-xl p-4">
                  <Loader2 className="w-5 h-5 animate-spin shrink-0" />
                  <span className="text-sm">Plan is queued. Refresh in a moment.</span>
                </div>
              ) : editMode ? (
                <textarea
                  value={editedPlan}
                  onChange={e => setEditedPlan(e.target.value)}
                  className="w-full h-96 px-3 py-2 rounded-xl border border-gray-200 focus:border-green-500 focus:ring-1 focus:ring-green-100 outline-none text-sm font-mono resize-none"
                />
              ) : (
                <div className="p-1 text-sm text-gray-800 leading-relaxed">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      // Tables: horizontally scrollable on mobile
                      table: ({ children }) => (
                        <div className="overflow-x-auto my-3 rounded-xl border border-gray-200">
                          <table className="min-w-full text-xs border-collapse">{children}</table>
                        </div>
                      ),
                      thead: ({ children }) => <thead className="bg-green-50">{children}</thead>,
                      th: ({ children }) => (
                        <th className="px-3 py-2 text-left font-semibold text-green-800 border-b border-gray-200 whitespace-nowrap">{children}</th>
                      ),
                      td: ({ children }) => (
                        <td className="px-3 py-2 border-b border-gray-100 align-top">{children}</td>
                      ),
                      tr: ({ children }) => <tr className="even:bg-gray-50 hover:bg-green-50/40 transition-colors">{children}</tr>,
                      // Headings
                      h1: ({ children }) => <h1 className="text-lg font-bold text-gray-900 mt-4 mb-2 border-b border-gray-200 pb-1">{children}</h1>,
                      h2: ({ children }) => <h2 className="text-base font-bold text-green-800 mt-5 mb-2">{children}</h2>,
                      h3: ({ children }) => <h3 className="text-sm font-bold text-gray-800 mt-4 mb-1">{children}</h3>,
                      // Strong bold
                      strong: ({ children }) => <strong className="font-bold text-gray-900">{children}</strong>,
                      // Blockquote (used for tips)
                      blockquote: ({ children }) => (
                        <blockquote className="border-l-4 border-green-400 bg-green-50 px-3 py-2 my-2 rounded-r-lg text-green-900 text-xs">{children}</blockquote>
                      ),
                      // Paragraphs
                      p: ({ children }) => <p className="mb-2 text-gray-700">{children}</p>,
                      // Horizontal rule
                      hr: () => <hr className="my-4 border-gray-200" />,
                    }}
                  >
                    {planText || "Plan content is empty."}
                  </ReactMarkdown>
                </div>
              )}
            </div>
          )}

          {activeTab === "profile" && detail && (
            <div className="p-5 space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <InfoCard label="Age" value={`${detail.age} years`} />
                <InfoCard label="Gender" value={detail.gender} />
                <InfoCard label="Height" value={`${detail.height_cm} cm`} />
                <InfoCard label="Weight" value={`${detail.weight_kg} kg`} />
                <InfoCard label="Goal" value={goalMap[detail.goal] || detail.goal} />
                <InfoCard label="Target Weight" value={detail.target_weight_kg ? `${detail.target_weight_kg} kg` : "—"} />
              </div>
              <div className="bg-green-50 rounded-xl p-4 grid grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="text-lg font-bold text-green-700">{detail.bmr}</div>
                  <div className="text-xs text-gray-500">BMR (kcal)</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-green-700">{detail.tdee}</div>
                  <div className="text-xs text-gray-500">TDEE (kcal)</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-green-700">{Math.round(detail.calorie_target)}</div>
                  <div className="text-xs text-gray-500">Target (kcal)</div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <InfoCard label="Protein" value={`${detail.protein_target_g}g`} />
                <InfoCard label="Carbs" value={`${detail.carb_target_g}g`} />
                <InfoCard label="Fat" value={`${detail.fat_target_g}g`} />
              </div>
              <InfoCard label="Medical Conditions" value={detail.medical_conditions?.join(", ") || "None"} />
              <InfoCard label="Food Allergies" value={detail.food_allergies?.join(", ") || "None"} />
              <InfoCard label="Diet Type" value={detail.diet_type} />
              <InfoCard label="Activity Level" value={detail.activity_level} />
              <InfoCard label="Exercise Preferences" value={detail.exercise_preference?.length ? detail.exercise_preference.join(", ") : "None"} />
              <InfoCard label="Location" value={[detail.city, detail.state].filter(Boolean).join(", ") || "—"} />
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="p-4 border-t border-gray-100 bg-gray-50 space-y-2">
          {plan && (
            <div className="flex gap-2 flex-wrap">
              {editMode ? (
                <>
                  <button onClick={handleSave} disabled={loading}
                    className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2.5 rounded-xl transition-all disabled:opacity-60">
                    <Save className="w-4 h-4" /> Save Changes
                  </button>
                  <button onClick={() => setEditMode(false)} disabled={loading}
                    className="flex items-center gap-1.5 bg-gray-200 hover:bg-gray-300 text-gray-700 text-sm font-semibold px-4 py-2.5 rounded-xl transition-all">
                    Cancel
                  </button>
                </>
              ) : (
                <button onClick={() => setEditMode(true)}
                  className="flex items-center gap-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 text-sm font-semibold px-4 py-2.5 rounded-xl transition-all">
                  <Edit3 className="w-4 h-4" /> Edit Plan
                </button>
              )}

              {(plan.status === "pending" || plan.status === "edited") && (
                <button onClick={handleApprove} disabled={loading}
                  className="flex items-center gap-1.5 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold px-4 py-2.5 rounded-xl transition-all disabled:opacity-60">
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                  Approve Plan
                </button>
              )}

              {(plan.status === "approved" || plan.status === "edited") && client.email && (
                <button onClick={handleSendEmail} disabled={loading}
                  className="flex items-center gap-1.5 bg-purple-600 hover:bg-purple-700 text-white text-sm font-semibold px-4 py-2.5 rounded-xl transition-all disabled:opacity-60">
                  <Send className="w-4 h-4" /> Send Email
                </button>
              )}

              {(plan.status === "approved" || plan.status === "sent") && (
                <>
                  <button onClick={() => handleDownload(adminApi.getPdfDownloadUrl(plan.id), `NutriVeda_Plan_${client.full_name.replace(/ /g,"_")}.pdf`)}
                    className="flex items-center gap-1.5 bg-orange-50 hover:bg-orange-100 text-orange-700 text-sm font-semibold px-4 py-2.5 rounded-xl transition-all">
                    <Download className="w-4 h-4" /> Download PDF
                  </button>
                  <button onClick={() => handleDownload(adminApi.getWordDownloadUrl(plan.id), `NutriVeda_Plan_${client.full_name.replace(/ /g,"_")}.docx`)}
                    className="flex items-center gap-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 text-sm font-semibold px-4 py-2.5 rounded-xl transition-all">
                    <File className="w-4 h-4" /> Download Word
                  </button>
                  <button onClick={() => handleDownload(adminApi.getAdminDocUrl(plan.id), `NutriVeda_SourceReport_Plan${plan.id}.docx`)}
                    title="Admin-only: shows exactly which MHB study files were used to generate this plan"
                    className="flex items-center gap-1.5 bg-purple-50 hover:bg-purple-100 text-purple-700 text-sm font-semibold px-4 py-2.5 rounded-xl transition-all">
                    <FileText className="w-4 h-4" /> Source Report
                  </button>
                </>
              )}

              <button onClick={handleRegenerate} disabled={loading}
                className={`flex items-center gap-1.5 text-sm font-semibold px-3 py-2.5 rounded-xl transition-all disabled:opacity-60 ml-auto relative ${
                  chatMessages.filter(m => m.role === "user").length > 0
                    ? "bg-orange-100 hover:bg-orange-200 text-orange-700 ring-1 ring-orange-300"
                    : "bg-gray-100 hover:bg-gray-200 text-gray-600"
                }`}
                title={chatMessages.filter(m => m.role === "user").length > 0
                  ? `Regenerate (Revision ${(plan.regeneration_count || 0) + 1}) with ${chatMessages.filter(m => m.role === "user").length} new instruction(s)`
                  : `Regenerate plan${(plan.regeneration_count || 0) > 0 ? ` (Revision ${(plan.regeneration_count || 0) + 1})` : ""}`}
              >
                <RefreshCw className="w-4 h-4" />
                Regenerate
                {(plan.regeneration_count || 0) > 0 && chatMessages.filter(m => m.role === "user").length === 0 && (
                  <span className="text-[10px] text-orange-400 font-normal">×{plan.regeneration_count}</span>
                )}
                {chatMessages.filter(m => m.role === "user").length > 0 && (
                  <span className="bg-orange-500 text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
                    {chatMessages.filter(m => m.role === "user").length}
                  </span>
                )}
              </button>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}

// ─── Revision History ─────────────────────────────────────────────────────────

function RevisionHistory({ history }: { history: ChatSession[] }) {
  const [open, setOpen] = useState(false);
  const total = history.reduce((sum, s) => sum + (s.instructions?.length || 0), 0);

  return (
    <div className="mb-4 border border-orange-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-orange-50 hover:bg-orange-100 transition-colors text-left"
      >
        <span className="text-xs font-semibold text-orange-700">
          📋 Revision History — {history.length} session{history.length !== 1 ? "s" : ""}, {total} instruction{total !== 1 ? "s" : ""}
        </span>
        <span className="text-orange-400 text-xs">{open ? "▲ Hide" : "▼ Show"}</span>
      </button>
      {open && (
        <div className="divide-y divide-orange-100 bg-white">
          {history.map((session) => (
            <div key={session.revision} className="px-4 py-3">
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-xs font-bold text-orange-600">Session {session.revision}</span>
                {session.timestamp && (
                  <span className="text-xs text-gray-400">{session.timestamp.slice(0, 10)}</span>
                )}
              </div>
              <ul className="space-y-1">
                {(session.instructions || []).map((inst, j) => (
                  <li key={j} className="text-xs text-gray-700 flex gap-2">
                    <span className="text-orange-400 shrink-0">•</span>
                    <span>{inst}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Admin Chatbot ────────────────────────────────────────────────────────────

interface ChatMsg { role: "user" | "assistant"; content: string; }

function AdminChatBot({
  planId, clientName, messages, onMessagesChange
}: {
  planId: number | null;
  clientName: string | null;
  messages: ChatMsg[];
  onMessagesChange: (msgs: ChatMsg[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sources, setSources] = useState<string[]>([]);
  const endRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom on new message
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Reset messages on plan change
  useEffect(() => {
    onMessagesChange([]);
    setSources([]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planId]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;
    const newHistory: ChatMsg[] = [...messages, { role: "user", content: text }];
    onMessagesChange(newHistory);
    setInput("");
    setLoading(true);
    try {
      const res = await adminApi.chat(text, planId, messages);
      const reply = res.data.reply as string;
      const srcs = (res.data.sources as string[]) || [];
      onMessagesChange([...newHistory, { role: "assistant", content: reply }]);
      setSources(srcs);
    } catch {
      onMessagesChange([...newHistory, { role: "assistant", content: "Sorry, the assistant is unavailable right now. Check if the backend is running." }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen(o => !o)}
        className="fixed bottom-8 right-4 sm:bottom-6 sm:right-6 z-50 w-14 h-14 bg-green-600 hover:bg-green-700 text-white rounded-full shadow-xl flex items-center justify-center transition-all hover:scale-105 active:scale-95"
        title="NutriVeda AI Assistant"
      >
        {open ? <X className="w-6 h-6" /> : <MessageCircle className="w-6 h-6" />}
        {!open && messages.length > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">
            {messages.filter(m => m.role === "assistant").length}
          </span>
        )}
      </button>

      {/* Chat panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="fixed bottom-28 right-4 sm:bottom-24 sm:right-6 z-50 w-[380px] max-w-[calc(100vw-1rem)] bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col overflow-hidden"
            style={{ height: "min(520px, calc(100dvh - 140px))" }}
          >
            {/* Header */}
            <div className="bg-green-600 px-4 py-3 flex items-center gap-3 shrink-0">
              <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-white font-bold text-sm">NutriVeda Assistant</div>
                <div className="text-green-100 text-xs truncate">
                  {planId && clientName
                    ? `Context: ${clientName}'s plan`
                    : "General nutrition knowledge"}
                </div>
              </div>
              <button onClick={() => setOpen(false)} className="text-white/70 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
              {messages.length === 0 && (
                <div className="text-center text-gray-400 text-sm py-8">
                  <Bot className="w-10 h-10 mx-auto mb-3 opacity-30" />
                  <p className="font-medium">Ask anything about nutrition</p>
                  <p className="text-xs mt-1 text-gray-300">Plan edits · Macro advice · MHB knowledge</p>
                  {planId && (
                    <div className="mt-4 space-y-2">
                      {[
                        "Review this plan for any issues",
                        "Suggest better breakfast options",
                        "Is the protein target correct for this client?",
                      ].map(q => (
                        <button
                          key={q}
                          onClick={() => { setInput(q); }}
                          className="block w-full text-left text-xs bg-white border border-gray-200 rounded-lg px-3 py-2 hover:border-green-400 hover:bg-green-50 transition-colors text-gray-600"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
                    msg.role === "user"
                      ? "bg-green-600 text-white rounded-br-sm"
                      : "bg-white text-gray-800 border border-gray-100 rounded-bl-sm shadow-sm"
                  }`}>
                    {msg.content}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
                    <div className="flex gap-1 items-center">
                      <span className="w-2 h-2 bg-green-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                      <span className="w-2 h-2 bg-green-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                      <span className="w-2 h-2 bg-green-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={endRef} />
            </div>

            {/* Sources */}
            {sources.length > 0 && (
              <div className="px-4 py-2 bg-green-50 border-t border-green-100 flex items-center gap-2 shrink-0">
                <BookOpen className="w-3 h-3 text-green-600 shrink-0" />
                <span className="text-xs text-green-700 truncate">
                  Sources: {sources.slice(0, 3).join(", ")}
                </span>
              </div>
            )}

            {/* Input */}
            <div className="p-3 border-t border-gray-100 bg-white shrink-0 flex gap-2">
              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Ask about nutrition, plan edits, MHB knowledge..."
                rows={2}
                className="flex-1 text-sm px-3 py-2 rounded-xl border border-gray-200 focus:border-green-500 focus:ring-1 focus:ring-green-100 outline-none resize-none text-gray-800 placeholder-gray-400"
              />
              <button
                onClick={sendMessage}
                disabled={!input.trim() || loading}
                className="self-end bg-green-600 hover:bg-green-700 disabled:opacity-40 text-white rounded-xl p-2.5 transition-all"
              >
                <SendHorizonal className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 p-3">
      <div className="text-xs text-gray-400 font-medium mb-1">{label}</div>
      <div className="text-sm font-semibold text-gray-800 capitalize">{value}</div>
    </div>
  );
}

// ─── Pricing Panel ────────────────────────────────────────────────────────────

interface PriceOption { inr: number; label: string; usd: number; eur: number; gbp: number; aed: number; sgd: number; }
interface AdminPriceConfig { active_price_inr: number; max_price_inr: number; discount_pct: number; prices: PriceOption[]; }

function PricingPanel({ token }: { token: string }) {
  const [config, setConfig] = useState<AdminPriceConfig | null>(null);
  const [selected, setSelected] = useState<number>(1999);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    adminApi.getPriceConfig(token)
      .then(r => {
        setConfig(r.data);
        setSelected(r.data.active_price_inr);
      })
      .catch(() => {});
  }, [token]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await adminApi.updatePriceConfig(token, selected);
      toast.success("Price updated successfully!");
      adminApi.getPriceConfig(token).then(r => setConfig(r.data)).catch(() => {});
    } catch {
      toast.error("Failed to update price.");
    } finally {
      setSaving(false);
    }
  };

  if (!config) return null;

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mb-6">
      <div className="flex items-center justify-between mb-5">
        <h2 className="font-bold text-gray-900 flex items-center gap-2 text-base">
          💰 Pricing Settings
        </h2>
        <span className="text-xs text-gray-400 bg-gray-50 px-2 py-1 rounded-lg">
          Active: ₹{config.active_price_inr.toLocaleString("en-IN")}
          {config.discount_pct > 0 && ` (${config.discount_pct}% off)`}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
        {config.prices.map(p => {
          const isActive = config.active_price_inr === p.inr;
          const discPct = Math.round((config.max_price_inr - p.inr) / config.max_price_inr * 100);
          return (
            <button
              key={p.inr}
              type="button"
              onClick={() => setSelected(p.inr)}
              className={`relative text-left p-4 rounded-xl border-2 transition-all ${
                selected === p.inr
                  ? "border-green-500 bg-green-50"
                  : "border-gray-200 hover:border-green-300 hover:bg-gray-50"
              }`}
            >
              {isActive && (
                <span className="absolute top-2 right-2 text-xs bg-green-600 text-white px-1.5 py-0.5 rounded-full font-semibold">
                  Active
                </span>
              )}
              <div className="font-bold text-gray-900 text-lg">₹{p.inr.toLocaleString("en-IN")}</div>
              <div className="text-xs text-gray-500 font-medium mb-2">{p.label}</div>
              {discPct > 0 && (
                <div className="text-xs text-orange-600 font-semibold mb-2">{discPct}% OFF max price</div>
              )}
              <div className="text-xs text-gray-400 space-y-0.5">
                <div>${p.usd} · €{p.eur} · £{p.gbp}</div>
                <div>AED {p.aed} · SGD {p.sgd}</div>
              </div>
            </button>
          );
        })}
      </div>

      <button
        onClick={handleSave}
        disabled={saving || selected === config.active_price_inr}
        className="bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold px-5 py-2.5 rounded-xl text-sm transition-all flex items-center gap-2"
      >
        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
        {saving ? "Saving..." : "Save Price"}
      </button>
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────

export default function AdminDashboard() {
  const router = useRouter();
  const [stats, setStats] = useState<Stats | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [filter, setFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMsg[]>([]);
  const [showSettings, setShowSettings] = useState(false);
  const [adminToken, setAdminToken] = useState("");

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, clientsRes] = await Promise.all([
        adminApi.getStats(),
        adminApi.getClients(),
      ]);
      setStats(statsRes.data);
      setClients(clientsRes.data);
    } catch {
      toast.error("Failed to load data. Check if backend is running.");
      router.push("/admin");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    const token = localStorage.getItem("nutriveda_admin_token");
    if (!token) { router.push("/admin"); return; }
    setAdminToken(token);
    fetchData();
  }, [fetchData, router]);

  const openClient = async (client: Client) => {
    setSelectedClient(client);
    setSelectedPlan(null);
    setPanelOpen(true);
    if (client.plan_id) {
      try {
        const res = await adminApi.getPlan(client.plan_id);
        setSelectedPlan(res.data);
      } catch {
        toast.error("Could not load plan");
      }
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("nutriveda_admin_token");
    router.push("/admin");
  };

  const filteredClients = clients
    .filter(c => filter === "all" || c.plan_status === filter || (!c.plan_status && filter === "no_plan"))
    .filter(c => c.full_name.toLowerCase().includes(search.toLowerCase()) ||
      c.email?.toLowerCase().includes(search.toLowerCase()));

  const goalLabel: Record<string, string> = {
    lose_weight: "Weight Loss", gain_muscle: "Muscle Gain",
    maintain: "Maintenance", improve_health: "Health",
    medical_management: "Medical", sports_nutrition: "Sports",
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-green-600 mx-auto mb-3" />
          <p className="text-gray-500">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Nav */}
      <nav className="bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between sticky top-0 z-40 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-green-600 rounded-lg flex items-center justify-center">
            <span className="text-white">🌿</span>
          </div>
          <div>
            <div className="font-bold text-gray-900">NutriVeda</div>
            <div className="text-xs text-green-600">Admin Dashboard</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={fetchData} className="p-2 hover:bg-gray-100 rounded-lg transition-colors" title="Refresh">
            <RefreshCw className="w-4 h-4 text-gray-500" />
          </button>
          <button
            onClick={() => setShowSettings(s => !s)}
            className={`flex items-center gap-2 text-sm font-medium px-3 py-2 rounded-lg transition-all ${
              showSettings ? "bg-green-50 text-green-700" : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            💰 Pricing
          </button>
          <button onClick={handleLogout}
            className="flex items-center gap-2 text-sm text-gray-600 hover:text-red-600 font-medium px-3 py-2 rounded-lg hover:bg-red-50 transition-all">
            <LogOut className="w-4 h-4" /> Logout
          </button>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* Pricing settings panel */}
        {showSettings && adminToken && <PricingPanel token={adminToken} />}

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {[
              { label: "Total Clients", value: stats.total_clients, icon: Users, color: "bg-blue-500", bg: "bg-blue-50" },
              { label: "Pending Review", value: stats.pending_review, icon: Clock, color: "bg-yellow-500", bg: "bg-yellow-50" },
              { label: "Approved Plans", value: stats.approved, icon: CheckCircle, color: "bg-green-600", bg: "bg-green-50" },
              { label: "Sent to Clients", value: stats.sent_to_client, icon: Mail, color: "bg-purple-600", bg: "bg-purple-50" },
            ].map(s => (
              <motion.div
                key={s.label}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`${s.bg} rounded-2xl p-5 border border-white shadow-sm`}
              >
                <div className={`w-10 h-10 ${s.color} rounded-xl flex items-center justify-center mb-3`}>
                  <s.icon className="w-5 h-5 text-white" />
                </div>
                <div className="text-3xl font-bold text-gray-900">{s.value}</div>
                <div className="text-sm text-gray-500 font-medium">{s.label}</div>
              </motion.div>
            ))}
          </div>
        )}

        {/* Filters + Search */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 mb-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search by name or email..."
              className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 focus:border-green-500 focus:ring-2 focus:ring-green-100 outline-none text-sm"
            />
            <div className="flex gap-2 flex-wrap">
              {[
                { id: "all", label: "All" },
                { id: "pending", label: "⏳ Pending" },
                { id: "approved", label: "✅ Approved" },
                { id: "sent", label: "📧 Sent" },
                { id: "no_plan", label: "⌛ No Plan" },
              ].map(f => (
                <button
                  key={f.id}
                  onClick={() => setFilter(f.id)}
                  className={`px-3 py-2 rounded-lg text-xs font-semibold transition-all ${
                    filter === f.id ? "bg-green-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Client Table */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="p-5 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-bold text-gray-900 flex items-center gap-2">
              <FileText className="w-5 h-5 text-green-600" />
              Client Submissions
              <span className="text-sm font-normal text-gray-400 ml-1">({filteredClients.length})</span>
            </h2>
          </div>

          {filteredClients.length === 0 ? (
            <div className="p-12 text-center text-gray-400">
              <Users className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>No clients found</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-50">
              {filteredClients.map((client, i) => (
                <motion.div
                  key={client.id}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  onClick={() => openClient(client)}
                  className="flex items-center gap-4 p-4 hover:bg-gray-50 cursor-pointer transition-colors group"
                >
                  {/* Avatar */}
                  <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center text-green-700 font-bold text-sm shrink-0">
                    {client.full_name[0].toUpperCase()}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-gray-900 text-sm truncate">{client.full_name}</div>
                    <div className="text-xs text-gray-400 truncate">
                      {client.email || "No email"} •
                      {client.age && ` ${client.age}y`} •
                      {goalLabel[client.goal] || client.goal}
                    </div>
                  </div>

                  {/* Status */}
                  <StatusBadge status={client.plan_status} />

                  {/* Date */}
                  <div className="text-xs text-gray-400 hidden sm:block shrink-0">
                    {new Date(client.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                  </div>

                  <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-green-500 transition-colors shrink-0" />
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Plan Panel */}
      <AnimatePresence>
        {panelOpen && selectedClient && (
          <PlanPanel
            client={selectedClient}
            plan={selectedPlan}
            chatMessages={chatMessages}
            onClose={() => { setPanelOpen(false); setSelectedClient(null); }}
            onRefresh={() => {
              fetchData();
              if (selectedClient?.plan_id) {
                adminApi.getPlan(selectedClient.plan_id).then(r => setSelectedPlan(r.data)).catch(() => {});
              }
            }}
          />
        )}
      </AnimatePresence>

      {/* Floating AI Chatbot */}
      <AdminChatBot
        planId={selectedPlan?.id ?? null}
        clientName={selectedClient?.full_name ?? null}
        messages={chatMessages}
        onMessagesChange={setChatMessages}
      />
    </div>
  );
}
