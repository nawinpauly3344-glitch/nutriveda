"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, CheckCircle, Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import { intakeApi } from "@/lib/api";

// ─── Price config type ────────────────────────────────────────────────────────

interface PriceConfigData {
  active_price_inr: number;
  max_price_inr: number;
  discount_pct: number;
  razorpay_key_id: string;
  payment_enabled: boolean;
}

// ─── Types ───────────────────────────────────────────────────────────────────

interface FormState {
  // Step 1
  full_name: string;
  age: string;
  gender: string;
  height_unit: "cm" | "ftin";
  height_cm: string;
  height_ft: string;
  height_in: string;
  weight_unit: "kg" | "lbs";
  weight_kg: string;
  weight_lbs: string;
  goal: string;
  target_weight_kg: string;
  timeline: string;
  email: string;
  phone: string;
  // Step 2
  medical_conditions: string[];
  other_condition: string;
  current_medications: string;
  food_allergies: string[];
  other_allergy: string;
  digestive_issues: string;
  digestive_description: string;
  menstrual_irregularities: boolean;
  is_pregnant: boolean;
  is_breastfeeding: boolean;
  // Step 3
  activity_level: string;
  exercise_preference: string[];
  exercise_type: string;
  exercise_frequency: string;
  sleep_hours: string;
  stress_level: string;
  work_type: string;
  meals_per_day: string;
  meal_timings: string;
  // Step 4
  diet_type: string;
  food_dislikes: string;
  cuisine_preference: string[];
  city: string;
  state: string;
  cooking_situation: string;
  // Step 5
  current_diet_description: string;
  water_intake_liters: string;
  current_supplements: string;
  alcohol_habit: string;
  smoking_habit: string;
  protein_intake_level: string;
}

const INITIAL_STATE: FormState = {
  full_name: "", age: "", gender: "",
  height_unit: "cm", height_cm: "", height_ft: "", height_in: "",
  weight_unit: "kg", weight_kg: "", weight_lbs: "",
  goal: "", target_weight_kg: "", timeline: "", email: "", phone: "",
  medical_conditions: [], other_condition: "", current_medications: "",
  food_allergies: [], other_allergy: "",
  digestive_issues: "no", digestive_description: "",
  menstrual_irregularities: false, is_pregnant: false, is_breastfeeding: false,
  activity_level: "", exercise_preference: [], exercise_type: "", exercise_frequency: "",
  sleep_hours: "", stress_level: "", work_type: "", meals_per_day: "", meal_timings: "",
  diet_type: "", food_dislikes: "", cuisine_preference: [],
  city: "", state: "", cooking_situation: "",
  current_diet_description: "", water_intake_liters: "", current_supplements: "",
  alcohol_habit: "none", smoking_habit: "none", protein_intake_level: "",
};

const STEPS = [
  { num: 1, title: "Basic Info", icon: "👤" },
  { num: 2, title: "Health & Medical", icon: "🏥" },
  { num: 3, title: "Lifestyle", icon: "🏃" },
  { num: 4, title: "Diet Preferences", icon: "🍽️" },
  { num: 5, title: "Current Diet", icon: "📝" },
];

// ─── Helper components ────────────────────────────────────────────────────────

function Label({ children }: { children: React.ReactNode }) {
  return <label className="block text-sm font-semibold text-gray-700 mb-2">{children}</label>;
}

function Input({ ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-green-500 focus:ring-2 focus:ring-green-100 outline-none transition-all text-gray-800 placeholder-gray-400"
    />
  );
}

function Textarea({ ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      rows={3}
      className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-green-500 focus:ring-2 focus:ring-green-100 outline-none transition-all text-gray-800 placeholder-gray-400 resize-none"
    />
  );
}

function Select({ children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement> & { children: React.ReactNode }) {
  return (
    <select
      {...props}
      className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-green-500 focus:ring-2 focus:ring-green-100 outline-none transition-all text-gray-800 bg-white"
    >
      {children}
    </select>
  );
}

function OptionCard({
  selected, onClick, label, description, icon
}: {
  selected: boolean; onClick: () => void;
  label: string; description?: string; icon?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
        selected
          ? "border-green-500 bg-green-50 shadow-sm"
          : "border-gray-200 hover:border-green-300 hover:bg-gray-50"
      }`}
    >
      <div className="flex items-center gap-3">
        {icon && <span className="text-xl">{icon}</span>}
        <div>
          <div className="font-semibold text-gray-900 text-sm">{label}</div>
          {description && <div className="text-xs text-gray-500 mt-0.5">{description}</div>}
        </div>
        {selected && <CheckCircle className="w-5 h-5 text-green-600 ml-auto shrink-0" />}
      </div>
    </button>
  );
}

function CheckBox({
  checked, onChange, label
}: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <label className="flex items-center gap-3 cursor-pointer p-3 rounded-xl hover:bg-gray-50 transition-colors">
      <div
        onClick={() => onChange(!checked)}
        className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
          checked ? "bg-green-600 border-green-600" : "border-gray-300"
        }`}
      >
        {checked && <CheckCircle className="w-3 h-3 text-white" />}
      </div>
      <span className="text-sm text-gray-700">{label}</span>
    </label>
  );
}

// ─── Step components ──────────────────────────────────────────────────────────

function Step1({ form, set }: { form: FormState; set: (k: keyof FormState, v: unknown) => void }) {
  const goals = [
    { id: "lose_weight", label: "Lose Weight", icon: "🔥", desc: "Safe fat loss" },
    { id: "gain_muscle", label: "Gain Muscle", icon: "💪", desc: "Build lean muscle" },
    { id: "gain_muscle_lose_fat", label: "Gain Muscle & Lose Fat", icon: "⚡", desc: "Body recomposition — build muscle and shed fat together" },
    { id: "maintain", label: "Maintain Weight", icon: "⚖️", desc: "Stay at current weight" },
    { id: "improve_health", label: "Improve Health", icon: "❤️", desc: "General wellness" },
    { id: "medical_management", label: "Medical / Condition Management", icon: "🩺", desc: "Diabetes, PCOS, Thyroid etc." },
    { id: "sports_nutrition", label: "Sports Nutrition", icon: "🏆", desc: "Athletic performance" },
  ];

  const heightInCm = () => {
    if (form.height_unit === "cm") return parseFloat(form.height_cm) || 0;
    const ft = parseFloat(form.height_ft) || 0;
    const inch = parseFloat(form.height_in) || 0;
    return Math.round((ft * 30.48) + (inch * 2.54));
  };

  const weightInKg = () => {
    if (form.weight_unit === "kg") return parseFloat(form.weight_kg) || 0;
    return Math.round((parseFloat(form.weight_lbs) || 0) / 2.205 * 10) / 10;
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <Label>Full Name *</Label>
          <Input
            placeholder="e.g. Priya Sharma"
            value={form.full_name}
            onChange={e => set("full_name", e.target.value)}
          />
        </div>
        <div>
          <Label>Age *</Label>
          <Input
            type="number" placeholder="25" min={10} max={100}
            value={form.age}
            onChange={e => set("age", e.target.value)}
          />
        </div>
      </div>

      <div>
        <Label>Gender *</Label>
        <div className="grid grid-cols-3 gap-3">
          {[{ id: "male", label: "Male", icon: "👨" }, { id: "female", label: "Female", icon: "👩" }, { id: "other", label: "Other", icon: "🧑" }].map(g => (
            <OptionCard key={g.id} selected={form.gender === g.id} onClick={() => set("gender", g.id)} label={g.label} icon={g.icon} />
          ))}
        </div>
      </div>

      {/* Height */}
      <div>
        <Label>Height *</Label>
        <div className="flex gap-2 mb-3">
          {["cm", "ftin"].map(u => (
            <button key={u} type="button" onClick={() => set("height_unit", u)}
              className={`px-4 py-2 rounded-lg text-sm font-semibold border transition-all ${form.height_unit === u ? "bg-green-600 text-white border-green-600" : "bg-white text-gray-600 border-gray-200"}`}>
              {u === "cm" ? "Centimeters" : "Feet & Inches"}
            </button>
          ))}
        </div>
        {form.height_unit === "cm" ? (
          <div>
            <Input type="number" placeholder="165" min={50} max={300}
              value={form.height_cm} onChange={e => set("height_cm", e.target.value)} />
            {form.height_cm && <p className="text-xs text-gray-400 mt-1">{form.height_cm} cm</p>}
          </div>
        ) : (
          <div className="flex gap-3">
            <div className="flex-1">
              <Input type="number" placeholder="5" min={1} max={9}
                value={form.height_ft} onChange={e => set("height_ft", e.target.value)} />
              <p className="text-xs text-gray-400 mt-1">Feet</p>
            </div>
            <div className="flex-1">
              <Input type="number" placeholder="8" min={0} max={11}
                value={form.height_in} onChange={e => set("height_in", e.target.value)} />
              <p className="text-xs text-gray-400 mt-1">Inches</p>
            </div>
          </div>
        )}
        {heightInCm() > 0 && (
          <p className="text-xs text-green-600 mt-1 font-medium">= {heightInCm()} cm</p>
        )}
      </div>

      {/* Weight */}
      <div>
        <Label>Current Weight *</Label>
        <div className="flex gap-2 mb-3">
          {["kg", "lbs"].map(u => (
            <button key={u} type="button" onClick={() => set("weight_unit", u)}
              className={`px-4 py-2 rounded-lg text-sm font-semibold border transition-all ${form.weight_unit === u ? "bg-green-600 text-white border-green-600" : "bg-white text-gray-600 border-gray-200"}`}>
              {u}
            </button>
          ))}
        </div>
        {form.weight_unit === "kg" ? (
          <Input type="number" placeholder="70" min={20} max={500}
            value={form.weight_kg} onChange={e => set("weight_kg", e.target.value)} />
        ) : (
          <div>
            <Input type="number" placeholder="155" min={40} max={1000}
              value={form.weight_lbs} onChange={e => set("weight_lbs", e.target.value)} />
            {form.weight_lbs && <p className="text-xs text-green-600 mt-1 font-medium">= {weightInKg()} kg</p>}
          </div>
        )}
      </div>

      {/* Goal */}
      <div>
        <Label>Primary Goal *</Label>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {goals.filter(g => g.id !== "gain_muscle_lose_fat").map(g => (
            <OptionCard key={g.id} selected={form.goal === g.id} onClick={() => set("goal", g.id)}
              label={g.label} description={g.desc} icon={g.icon} />
          ))}
          {/* Gain Muscle & Lose Weight — spans full width, same grid row */}
          <button
            type="button"
            onClick={() => set("goal", "gain_muscle_lose_fat")}
            className={`sm:col-span-2 w-full text-left p-4 rounded-xl border-2 transition-all relative ${
              form.goal === "gain_muscle_lose_fat"
                ? "border-orange-500 bg-orange-50 shadow-sm"
                : "border-orange-200 hover:border-orange-400 hover:bg-orange-50"
            }`}
          >
            <span className="absolute top-2.5 right-3 text-[10px] font-bold tracking-wider uppercase bg-orange-500 text-white px-2 py-0.5 rounded-full">
              Advanced
            </span>
            <div className="flex items-center gap-3 pr-24">
              <span className="text-xl shrink-0">⚡</span>
              <div className="min-w-0">
                <div className="font-semibold text-gray-900 text-sm">Gain Muscle &amp; Lose Weight</div>
                <div className="text-xs text-gray-500 mt-0.5">
                  Body recomposition — build muscle and shed fat simultaneously. High protein + 300 kcal deficit.
                </div>
              </div>
              {form.goal === "gain_muscle_lose_fat" && (
                <CheckCircle className="w-5 h-5 text-orange-500 ml-auto shrink-0" />
              )}
            </div>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <Label>Target Weight (optional)</Label>
          <Input type="number" placeholder="60 kg"
            value={form.target_weight_kg} onChange={e => set("target_weight_kg", e.target.value)} />
        </div>
        <div>
          <Label>Timeline / Expectation</Label>
          <Select value={form.timeline} onChange={e => set("timeline", e.target.value)}>
            <option value="">Select timeline</option>
            <option value="1 month">1 month</option>
            <option value="3 months">3 months</option>
            <option value="6 months">6 months</option>
            <option value="1 year">1 year</option>
            <option value="long term">Long term / lifestyle change</option>
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <Label>Email (to receive your plan)</Label>
          <Input type="email" placeholder="you@example.com"
            value={form.email} onChange={e => set("email", e.target.value)} />
        </div>
        <div>
          <Label>Phone (optional)</Label>
          <Input type="tel" placeholder="+91 9876543210"
            value={form.phone} onChange={e => set("phone", e.target.value)} />
        </div>
      </div>
    </div>
  );
}

function Step2({ form, set }: { form: FormState; set: (k: keyof FormState, v: unknown) => void }) {
  const conditions = [
    "Diabetes (Type 1)", "Diabetes (Type 2)", "Pre-Diabetes", "Thyroid (Hypo)", "Thyroid (Hyper)",
    "PCOS / PCOD", "High Blood Pressure", "Low Blood Pressure", "High Cholesterol",
    "Heart Disease", "Kidney Disease", "Liver Disease", "Anemia", "Arthritis", "None",
  ];

  const allergies = [
    "Gluten / Wheat", "Lactose / Dairy", "Nuts", "Soy", "Eggs",
    "Shellfish / Fish", "None",
  ];

  const toggleCondition = (c: string) => {
    const curr = form.medical_conditions;
    if (c === "None") { set("medical_conditions", ["None"]); return; }
    const filtered = curr.filter(x => x !== "None");
    set("medical_conditions", curr.includes(c) ? filtered.filter(x => x !== c) : [...filtered, c]);
  };

  const toggleAllergy = (a: string) => {
    const curr = form.food_allergies;
    if (a === "None") { set("food_allergies", ["None"]); return; }
    const filtered = curr.filter(x => x !== "None");
    set("food_allergies", curr.includes(a) ? filtered.filter(x => x !== a) : [...filtered, a]);
  };

  return (
    <div className="space-y-6">
      <div>
        <Label>Medical Conditions (select all that apply)</Label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {conditions.map(c => (
            <CheckBox key={c} checked={form.medical_conditions.includes(c)} onChange={() => toggleCondition(c)} label={c} />
          ))}
        </div>
        <div className="mt-3">
          <Input placeholder="Any other condition not listed above..."
            value={form.other_condition} onChange={e => set("other_condition", e.target.value)} />
        </div>
      </div>

      <div>
        <Label>Current Medications</Label>
        <Textarea placeholder="List any medications you are currently taking (or write 'None')"
          value={form.current_medications} onChange={e => set("current_medications", e.target.value)} />
      </div>

      <div>
        <Label>Food Allergies or Intolerances</Label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {allergies.map(a => (
            <CheckBox key={a} checked={form.food_allergies.includes(a)} onChange={() => toggleAllergy(a)} label={a} />
          ))}
        </div>
        <div className="mt-3">
          <Input placeholder="Any other allergy or intolerance..."
            value={form.other_allergy} onChange={e => set("other_allergy", e.target.value)} />
        </div>
      </div>

      <div>
        <Label>Digestive Issues?</Label>
        <div className="grid grid-cols-2 gap-3">
          {[{ id: "no", label: "No issues", icon: "👍" }, { id: "yes", label: "Yes, I have some", icon: "😟" }].map(o => (
            <OptionCard key={o.id} selected={form.digestive_issues === o.id}
              onClick={() => set("digestive_issues", o.id)} label={o.label} icon={o.icon} />
          ))}
        </div>
        {form.digestive_issues === "yes" && (
          <div className="mt-3">
            <Textarea placeholder="Describe your digestive issues (e.g. IBS, bloating, constipation, GERD...)"
              value={form.digestive_description} onChange={e => set("digestive_description", e.target.value)} />
          </div>
        )}
      </div>

      {/* Women's health */}
      <div className={`rounded-2xl border border-pink-100 bg-pink-50 p-5 ${form.gender !== "female" ? "opacity-50" : ""}`}>
        <div className="text-sm font-bold text-pink-700 mb-4">🌸 Women&apos;s Health (skip if not applicable)</div>
        <div className="space-y-2">
          <CheckBox checked={form.menstrual_irregularities} onChange={v => set("menstrual_irregularities", v)} label="Menstrual irregularities / PCOS symptoms" />
          <CheckBox checked={form.is_pregnant} onChange={v => set("is_pregnant", v)} label="Currently pregnant" />
          <CheckBox checked={form.is_breastfeeding} onChange={v => set("is_breastfeeding", v)} label="Currently breastfeeding" />
        </div>
      </div>
    </div>
  );
}

function Step3({ form, set }: { form: FormState; set: (k: keyof FormState, v: unknown) => void }) {
  const activityLevels = [
    { id: "sedentary", label: "Sedentary", icon: "🪑", desc: "Desk job, little or no exercise" },
    { id: "lightly_active", label: "Lightly Active", icon: "🚶", desc: "Light exercise 1-3 days/week" },
    { id: "moderately_active", label: "Moderately Active", icon: "🏃", desc: "Moderate exercise 3-5 days/week" },
    { id: "very_active", label: "Very Active", icon: "⚡", desc: "Hard exercise 6-7 days/week" },
    { id: "athlete", label: "Athlete / Physical Labor", icon: "🏋️", desc: "Intense daily training or physical job" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <Label>Activity Level *</Label>
        <div className="space-y-3">
          {activityLevels.map(a => (
            <OptionCard key={a.id} selected={form.activity_level === a.id}
              onClick={() => set("activity_level", a.id)} label={a.label} description={a.desc} icon={a.icon} />
          ))}
        </div>
      </div>

      <div>
        <Label>Exercise Preference (select all that apply)</Label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {[
            { id: "yoga", label: "Yoga", icon: "🧘", desc: "Asanas & breathwork" },
            { id: "gym", label: "Gym / Weights", icon: "🏋️", desc: "Strength training" },
            { id: "cardio", label: "Running / Cardio", icon: "🏃", desc: "Endurance & fat burn" },
            { id: "hiit", label: "HIIT", icon: "⚡", desc: "High-intensity intervals" },
            { id: "home_workout", label: "Home Workout", icon: "🏠", desc: "Bodyweight exercises" },
            { id: "dance", label: "Dance / Zumba", icon: "💃", desc: "Fun cardio dancing" },
          ].map(ex => {
            const selected = form.exercise_preference.includes(ex.id);
            return (
              <button
                key={ex.id}
                type="button"
                onClick={() => {
                  const curr = form.exercise_preference as string[];
                  set("exercise_preference", selected ? curr.filter(x => x !== ex.id) : [...curr, ex.id]);
                }}
                className={`w-full text-left p-3 rounded-xl border-2 transition-all ${
                  selected
                    ? "border-green-500 bg-green-50 shadow-sm"
                    : "border-gray-200 hover:border-green-300 hover:bg-gray-50"
                }`}
              >
                <div className="text-xl mb-1">{ex.icon}</div>
                <div className="font-semibold text-gray-900 text-sm">{ex.label}</div>
                <div className="text-xs text-gray-500 mt-0.5">{ex.desc}</div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <Label>Type of Exercise (details)</Label>
          <Input placeholder="e.g. Weight training, Yoga, Running..."
            value={form.exercise_type} onChange={e => set("exercise_type", e.target.value)} />
        </div>
        <div>
          <Label>Exercise Frequency</Label>
          <Select value={form.exercise_frequency} onChange={e => set("exercise_frequency", e.target.value)}>
            <option value="">Select frequency</option>
            <option value="no exercise">No exercise</option>
            <option value="1-2 days/week">1-2 days/week</option>
            <option value="3-4 days/week">3-4 days/week</option>
            <option value="5-6 days/week">5-6 days/week</option>
            <option value="daily">Daily</option>
            <option value="twice daily">Twice daily</option>
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <Label>Sleep Hours per Day</Label>
          <Select value={form.sleep_hours} onChange={e => set("sleep_hours", e.target.value)}>
            <option value="">Select</option>
            {["4", "5", "6", "7", "8", "9", "10"].map(h => (
              <option key={h} value={h}>{h} hours</option>
            ))}
          </Select>
        </div>
        <div>
          <Label>Stress Level</Label>
          <div className="grid grid-cols-3 gap-2">
            {[{ id: "low", label: "Low", icon: "😊" }, { id: "medium", label: "Medium", icon: "😐" }, { id: "high", label: "High", icon: "😰" }].map(s => (
              <OptionCard key={s.id} selected={form.stress_level === s.id}
                onClick={() => set("stress_level", s.id)} label={s.label} icon={s.icon} />
            ))}
          </div>
        </div>
      </div>

      <div>
        <Label>Work Type</Label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            { id: "desk_job", label: "Desk Job", icon: "💻", desc: "Office / WFH" },
            { id: "field_work", label: "Field Work", icon: "🚗", desc: "On-site / travel" },
            { id: "physical_labor", label: "Physical Labor", icon: "🏗️", desc: "Manual / factory" },
          ].map(w => (
            <OptionCard key={w.id} selected={form.work_type === w.id}
              onClick={() => set("work_type", w.id)} label={w.label} description={w.desc} icon={w.icon} />
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <Label>Meals Per Day</Label>
          <Select value={form.meals_per_day} onChange={e => set("meals_per_day", e.target.value)}>
            <option value="">Select</option>
            {["2", "3", "4", "5", "6"].map(n => <option key={n} value={n}>{n} meals</option>)}
          </Select>
        </div>
        <div>
          <Label>Meal Timings (approx.)</Label>
          <Input placeholder="e.g. 8am, 1pm, 4pm, 8pm"
            value={form.meal_timings} onChange={e => set("meal_timings", e.target.value)} />
        </div>
      </div>
    </div>
  );
}

function Step4({ form, set }: { form: FormState; set: (k: keyof FormState, v: unknown) => void }) {
  const diets = [
    { id: "vegetarian", label: "Vegetarian", icon: "🥗", desc: "No meat/fish/eggs, dairy OK" },
    { id: "non_vegetarian", label: "Non-Vegetarian", icon: "🍗", desc: "All foods including meat & fish" },
    { id: "eggetarian", label: "Eggetarian", icon: "🥚", desc: "Vegetarian + eggs" },
    { id: "vegan", label: "Vegan", icon: "🌱", desc: "No animal products at all" },
    { id: "jain", label: "Jain", icon: "🙏", desc: "No root vegetables, no meat" },
  ];

  const cuisines = [
    // Indian
    "North Indian", "South Indian", "Bengali", "Gujarati", "Maharashtrian",
    "Punjabi", "Rajasthani", "Kerala", "Andhra / Telangana",
    // Global
    "Mediterranean", "Middle Eastern", "East Asian (Chinese / Japanese / Korean)",
    "Southeast Asian (Thai / Vietnamese)", "Western / Continental",
    "Latin American (Mexican / Brazilian)", "African",
    "Any (based on my location)",
  ];

  const toggleCuisine = (c: string) => {
    const curr = form.cuisine_preference;
    set("cuisine_preference", curr.includes(c) ? curr.filter(x => x !== c) : [...curr, c]);
  };

  return (
    <div className="space-y-6">
      <div>
        <Label>Diet Type *</Label>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {diets.map(d => (
            <OptionCard key={d.id} selected={form.diet_type === d.id}
              onClick={() => set("diet_type", d.id)} label={d.label} description={d.desc} icon={d.icon} />
          ))}
        </div>
      </div>

      <div>
        <Label>Food Dislikes / Strong Preferences</Label>
        <Textarea placeholder="e.g. I hate bitter gourd, don't like fish, love paneer..."
          value={form.food_dislikes} onChange={e => set("food_dislikes", e.target.value)} />
      </div>

      <div>
        <Label>Cuisine Preference (select all that apply)</Label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {cuisines.map(c => (
            <CheckBox key={c} checked={form.cuisine_preference.includes(c)} onChange={() => toggleCuisine(c)} label={c} />
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <Label>City</Label>
          <Input placeholder="e.g. Mumbai, London, Dubai, New York..."
            value={form.city} onChange={e => set("city", e.target.value)} />
        </div>
        <div>
          <Label>State / Country</Label>
          <Input placeholder="e.g. Maharashtra, UK, UAE, USA..."
            value={form.state} onChange={e => set("state", e.target.value)} />
        </div>
      </div>

      <div>
        <Label>Cooking Situation</Label>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            { id: "cooks_at_home", label: "Cooks at Home", icon: "👩‍🍳", desc: "Full control over meals" },
            { id: "office_canteen", label: "Office Canteen / Mess", icon: "🍱", desc: "Limited options" },
            { id: "orders_food", label: "Orders Food", icon: "📱", desc: "Mostly delivery / restaurant" },
            { id: "mixed", label: "Mixed", icon: "🔀", desc: "Home + outside" },
          ].map(c => (
            <OptionCard key={c.id} selected={form.cooking_situation === c.id}
              onClick={() => set("cooking_situation", c.id)} label={c.label} description={c.desc} icon={c.icon} />
          ))}
        </div>
      </div>
    </div>
  );
}

function Step5({ form, set }: { form: FormState; set: (k: keyof FormState, v: unknown) => void }) {
  return (
    <div className="space-y-6">
      <div>
        <Label>What do you typically eat in a day? (be as detailed as possible)</Label>
        <Textarea
          rows={5}
          placeholder="e.g. Morning: 2 rotis with sabzi and chai. Lunch: rice, dal, salad. Evening: biscuits and tea. Dinner: 2 rotis, paneer curry..."
          value={form.current_diet_description}
          onChange={e => set("current_diet_description", e.target.value)}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <Label>Water Intake (liters per day)</Label>
          <Select value={form.water_intake_liters} onChange={e => set("water_intake_liters", e.target.value)}>
            <option value="">Select</option>
            {["0.5", "1", "1.5", "2", "2.5", "3", "3.5", "4"].map(l => (
              <option key={l} value={l}>{l} liters</option>
            ))}
          </Select>
        </div>
        <div>
          <Label>Current Supplements</Label>
          <Input placeholder="e.g. Vitamin D, Protein powder, None..."
            value={form.current_supplements} onChange={e => set("current_supplements", e.target.value)} />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <Label>Alcohol Consumption</Label>
          <Select value={form.alcohol_habit} onChange={e => set("alcohol_habit", e.target.value)}>
            <option value="none">None / Never</option>
            <option value="occasional">Occasionally (social)</option>
            <option value="weekly">1-2 drinks/week</option>
            <option value="frequent">3-5 drinks/week</option>
            <option value="daily">Daily</option>
          </Select>
        </div>
        <div>
          <Label>Smoking</Label>
          <Select value={form.smoking_habit} onChange={e => set("smoking_habit", e.target.value)}>
            <option value="none">Non-smoker</option>
            <option value="former">Former smoker</option>
            <option value="occasional">Occasional smoker</option>
            <option value="regular">Regular smoker</option>
            <option value="heavy">Heavy smoker</option>
          </Select>
        </div>
      </div>

      <div>
        <Label>Current Protein Intake <span className="text-red-500">*</span></Label>
        <p className="text-xs text-gray-500 mb-3">This helps us tailor the protein approach in your plan.</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            { id: "none_low", label: "No supplements, low protein diet", icon: "🥗", desc: "Mostly carbs/fat, rarely eat protein-rich foods" },
            { id: "none_moderate", label: "No supplements, moderate protein", icon: "🍗", desc: "Eat eggs, chicken, dal, paneer regularly" },
            { id: "supplements", label: "Taking protein supplements", icon: "🥤", desc: "Whey, plant protein, or similar" },
            { id: "high_food", label: "High protein through food only", icon: "💪", desc: "Very protein-focused diet, no supplements" },
            { id: "not_sure", label: "Not sure", icon: "❓", desc: "I don't track protein intake" },
          ].map(opt => (
            <OptionCard
              key={opt.id}
              selected={form.protein_intake_level === opt.id}
              onClick={() => set("protein_intake_level", opt.id)}
              label={opt.label}
              description={opt.desc}
              icon={opt.icon}
            />
          ))}
        </div>
      </div>

      {/* Summary preview */}
      <div className="bg-green-50 border border-green-200 rounded-2xl p-5">
        <div className="text-sm font-bold text-green-800 mb-3">🎯 Ready to generate your plan!</div>
        <p className="text-sm text-green-700 leading-relaxed">
          Your intake data will be processed through our <strong>BMR/TDEE calculator</strong> and
          our <strong>NutriVeda knowledge base</strong> to create a personalized diet & fitness plan with exercise guide tailored to your goals and location.
          Your nutritionist will review and approve it before you receive it.
        </p>
      </div>
    </div>
  );
}

// ─── Payment Wall ─────────────────────────────────────────────────────────────

function PaymentWall({
  form,
  priceConfig,
  onPaymentSuccess,
  onBack,
}: {
  form: FormState;
  priceConfig: PriceConfigData | null;
  onPaymentSuccess: (paymentId?: string) => void;
  onBack: () => void;
}) {
  const [paying, setPaying] = useState(false);
  const price = priceConfig?.active_price_inr ?? 1999;
  const maxPrice = priceConfig?.max_price_inr ?? 2999;
  const discountPct = priceConfig?.discount_pct ?? 0;

  const handlePay = async () => {
    setPaying(true);
    try {
      if (!priceConfig?.payment_enabled) {
        // Payment not configured yet — submit directly
        onPaymentSuccess(undefined);
        return;
      }
      // Razorpay flow — will be fully wired when keys are available
      onPaymentSuccess(undefined);
    } catch {
      toast.error("Payment failed. Please try again.");
      setPaying(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-white to-emerald-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white rounded-3xl shadow-2xl p-8 max-w-md w-full"
      >
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-8 h-8 text-green-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-1">
            You&apos;re all set, {form.full_name.split(" ")[0]}!
          </h2>
          <p className="text-gray-500 text-sm">
            Complete your payment to receive your personalized diet &amp; fitness plan
          </p>
        </div>

        {/* Price card */}
        <div className="bg-gradient-to-br from-green-500 to-emerald-600 rounded-2xl p-6 text-white text-center mb-6 relative overflow-hidden">
          {discountPct > 0 && (
            <div className="absolute top-3 right-3 bg-yellow-400 text-yellow-900 text-xs font-bold px-2 py-1 rounded-full">
              {discountPct}% OFF
            </div>
          )}
          <div className="text-sm font-medium opacity-80 mb-1">Personalized Diet &amp; Fitness Plan</div>
          {discountPct > 0 && (
            <div className="text-lg line-through opacity-60 mb-1">
              ₹{maxPrice.toLocaleString("en-IN")}
            </div>
          )}
          <div className="text-5xl font-bold mb-1">₹{price.toLocaleString("en-IN")}</div>
          <div className="text-sm opacity-80">One-time payment • Includes PDF plan</div>
        </div>

        {/* What you get */}
        <div className="space-y-2 mb-6">
          {[
            "Personalized weekly meal plan (Mon–Sun)",
            "Calorie & macro breakdown per meal",
            "Custom exercise schedule",
            "Food guide & daily habits",
            "Nutritionist review & approval",
            "Delivered to your email as PDF",
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-2 text-sm text-gray-600">
              <CheckCircle className="w-4 h-4 text-green-500 shrink-0" />
              <span>{item}</span>
            </div>
          ))}
        </div>

        {/* Pay button */}
        <button
          onClick={handlePay}
          disabled={paying}
          className="w-full bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white font-bold py-4 px-6 rounded-xl transition-all flex items-center justify-center gap-2 text-lg mb-3"
        >
          {paying ? <Loader2 className="w-5 h-5 animate-spin" /> : null}
          {paying ? "Processing..." : `Pay ₹${price.toLocaleString("en-IN")} →`}
        </button>

        <div className="text-center text-xs text-gray-400 mb-4">
          🔒 Secure payment · 100% safe · Instant confirmation
        </div>

        <button
          onClick={onBack}
          className="w-full text-sm text-gray-500 hover:text-gray-700 py-2 transition-colors"
        >
          ← Go back
        </button>
      </motion.div>
    </div>
  );
}

// ─── Success screen ────────────────────────────────────────────────────────────

function SuccessScreen({ data }: { data: { full_name: string; bmr: number; tdee: number; calorie_target: number; message: string } }) {
  const router = useRouter();
  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-white flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white rounded-3xl shadow-2xl p-8 max-w-lg w-full text-center"
      >
        <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <CheckCircle className="w-10 h-10 text-green-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">You&apos;re all set, {data.full_name?.split(" ")[0]}!</h2>
        <p className="text-gray-500 mb-8 leading-relaxed">{data.message}</p>

        {data.bmr > 0 && (
          <div className="grid grid-cols-3 gap-4 mb-8 p-4 bg-green-50 rounded-2xl">
            <div>
              <div className="text-2xl font-bold text-green-600">{data.bmr}</div>
              <div className="text-xs text-gray-500 font-medium">BMR (kcal)</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-600">{data.tdee}</div>
              <div className="text-xs text-gray-500 font-medium">TDEE (kcal)</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-600">{Math.round(data.calorie_target)}</div>
              <div className="text-xs text-gray-500 font-medium">Target (kcal)</div>
            </div>
          </div>
        )}

        <div className="space-y-3 text-left mb-8">
          {[
            "Your data has been saved securely",
            "Your personalized diet & fitness plan is being prepared",
            "Your nutritionist will review and approve it",
            "You'll receive your plan via email",
          ].map((s, i) => (
            <div key={i} className="flex items-center gap-3 text-sm text-gray-600">
              <CheckCircle className="w-5 h-5 text-green-500 shrink-0" />
              <span>{s}</span>
            </div>
          ))}
        </div>

        <button
          onClick={() => router.push("/")}
          className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-xl transition-all"
        >
          Back to Home
        </button>
      </motion.div>
    </div>
  );
}

// ─── Main Intake Page ─────────────────────────────────────────────────────────

function IntakeContent() {
  const searchParams = useSearchParams();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState<FormState>({ ...INITIAL_STATE });
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submitData, setSubmitData] = useState<Record<string, unknown>>({});
  const [showPayment, setShowPayment] = useState(false);
  const [priceConfig, setPriceConfig] = useState<PriceConfigData | null>(null);

  // Fetch price config on mount
  useEffect(() => {
    fetch("/api/payment/config")
      .then(r => r.json())
      .then(setPriceConfig)
      .catch(() => {});
  }, []);

  // Pre-fill goal from URL param
  useEffect(() => {
    const goal = searchParams.get("goal");
    if (goal) setForm(f => ({ ...f, goal }));
  }, [searchParams]);

  const set = (key: keyof FormState, value: unknown) => {
    setForm(f => ({ ...f, [key]: value }));
  };

  const getHeightCm = () => {
    if (form.height_unit === "cm") return parseFloat(form.height_cm) || 0;
    return Math.round((parseFloat(form.height_ft) || 0) * 30.48 + (parseFloat(form.height_in) || 0) * 2.54);
  };

  const getWeightKg = () => {
    if (form.weight_unit === "kg") return parseFloat(form.weight_kg) || 0;
    return Math.round((parseFloat(form.weight_lbs) || 0) / 2.205 * 10) / 10;
  };

  const validateStep = (): boolean => {
    if (step === 1) {
      if (!form.full_name.trim()) { toast.error("Please enter your name"); return false; }
      const age = parseInt(form.age);
      if (!form.age || isNaN(age)) { toast.error("Please enter your age"); return false; }
      if (age < 10 || age > 100) { toast.error("Age must be between 10 and 100"); return false; }
      if (!form.gender) { toast.error("Please select your gender"); return false; }
      if (getHeightCm() < 50 || getHeightCm() > 300) { toast.error("Please enter a valid height (50–300 cm)"); return false; }
      if (getWeightKg() < 20 || getWeightKg() > 500) { toast.error("Please enter a valid weight (20–500 kg)"); return false; }
      if (!form.goal) { toast.error("Please select your goal"); return false; }
    }
    if (step === 3) {
      if (!form.activity_level) { toast.error("Please select your activity level"); return false; }
    }
    if (step === 4) {
      if (!form.diet_type) { toast.error("Please select your diet type"); return false; }
    }
    if (step === 5) {
      if (!form.protein_intake_level) { toast.error("Please select your current protein intake level"); return false; }
    }
    return true;
  };

  const handleNext = () => {
    if (!validateStep()) return;
    if (step < 5) {
      setStep(s => s + 1);
    } else if (step === 5) {
      setShowPayment(true);
    }
  };

  const handleBack = () => {
    if (step > 1) setStep(s => s - 1);
  };

  const handleSubmit = async () => {
    if (!validateStep()) return;

    setLoading(true);
    try {
      const conditions = [...form.medical_conditions];
      if (form.other_condition.trim()) conditions.push(form.other_condition.trim());
      const allergies = [...form.food_allergies];
      if (form.other_allergy.trim()) allergies.push(form.other_allergy.trim());

      const payload = {
        step1: {
          full_name: form.full_name.trim(),
          age: parseInt(form.age),
          gender: form.gender,
          height_cm: getHeightCm(),
          weight_kg: getWeightKg(),
          goal: form.goal,
          target_weight_kg: form.target_weight_kg ? parseFloat(form.target_weight_kg) : null,
          timeline: form.timeline || null,
          email: form.email || null,
          phone: form.phone || null,
        },
        step2: {
          medical_conditions: conditions.filter(c => c !== "None"),
          current_medications: form.current_medications || null,
          food_allergies: allergies.filter(a => a !== "None"),
          digestive_issues: form.digestive_issues,
          digestive_description: form.digestive_description || null,
          menstrual_irregularities: form.menstrual_irregularities,
          is_pregnant: form.is_pregnant,
          is_breastfeeding: form.is_breastfeeding,
        },
        step3: {
          activity_level: form.activity_level,
          exercise_preference: form.exercise_preference,
          exercise_type: form.exercise_type || null,
          exercise_frequency: form.exercise_frequency || null,
          sleep_hours: form.sleep_hours ? parseFloat(form.sleep_hours) : null,
          stress_level: form.stress_level || null,
          work_type: form.work_type || null,
          meals_per_day: form.meals_per_day ? parseInt(form.meals_per_day) : null,
          meal_timings: form.meal_timings || null,
        },
        step4: {
          diet_type: form.diet_type,
          food_dislikes: form.food_dislikes || null,
          cuisine_preference: form.cuisine_preference,
          city: form.city || null,
          state: form.state || null,
          cooking_situation: form.cooking_situation || null,
        },
        step5: {
          current_diet_description: form.current_diet_description || null,
          water_intake_liters: form.water_intake_liters ? parseFloat(form.water_intake_liters) : null,
          current_supplements: form.current_supplements || null,
          alcohol_habit: form.alcohol_habit,
          smoking_habit: form.smoking_habit,
          protein_intake_level: form.protein_intake_level || null,
        },
      };

      const res = await intakeApi.submit(payload);
      setSubmitData(res.data);
      setSubmitted(true);
      toast.success("Form submitted successfully!");
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const detail = error?.response?.data?.detail;
      let msg = "Submission failed. Please try again.";
      if (typeof detail === "string") msg = detail;
      else if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0] as { msg?: string; loc?: string[] };
        msg = first.msg || msg;
      }
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return <SuccessScreen data={submitData as { full_name: string; bmr: number; tdee: number; calorie_target: number; message: string }} />;
  }

  if (showPayment) {
    return (
      <PaymentWall
        form={form}
        priceConfig={priceConfig}
        onPaymentSuccess={(_paymentId) => {
          setShowPayment(false);
          handleSubmit();
        }}
        onBack={() => setShowPayment(false)}
      />
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-white to-white">
      {/* Header */}
      <div className="bg-white border-b border-gray-100 py-4 px-4 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 bg-green-600 rounded-lg flex items-center justify-center text-white text-sm">🌿</div>
            <span className="font-bold text-gray-900">NutriVeda — Intake Form</span>
          </div>

          {/* Step indicators */}
          <div className="flex items-center gap-1">
            {STEPS.map((s, i) => (
              <div key={s.num} className="flex items-center flex-1">
                <div className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  step === s.num ? "bg-green-600 text-white" :
                  step > s.num ? "bg-green-100 text-green-700" :
                  "bg-gray-100 text-gray-400"
                }`}>
                  <span>{s.icon}</span>
                  <span className="hidden sm:inline">{s.title}</span>
                </div>
                {i < STEPS.length - 1 && (
                  <div className={`flex-1 h-0.5 mx-1 ${step > s.num ? "bg-green-400" : "bg-gray-200"}`} />
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Form */}
      <div className="max-w-2xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900">
            {STEPS[step - 1].icon} {STEPS[step - 1].title}
          </h2>
          <p className="text-gray-500 text-sm mt-1">
            Step {step} of {STEPS.length}
          </p>
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.25 }}
          >
            {step === 1 && <Step1 form={form} set={set} />}
            {step === 2 && <Step2 form={form} set={set} />}
            {step === 3 && <Step3 form={form} set={set} />}
            {step === 4 && <Step4 form={form} set={set} />}
            {step === 5 && <Step5 form={form} set={set} />}
          </motion.div>
        </AnimatePresence>

        {/* Navigation */}
        <div className="flex gap-3 mt-8 pt-6 border-t border-gray-100">
          {step > 1 && (
            <button
              onClick={handleBack}
              className="flex items-center gap-2 px-6 py-3 rounded-xl border border-gray-200 text-gray-700 font-semibold hover:bg-gray-50 transition-all"
            >
              <ChevronLeft className="w-4 h-4" /> Back
            </button>
          )}
          {step < 5 ? (
            <button
              onClick={handleNext}
              className="flex-1 bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-xl transition-all flex items-center justify-center gap-2 hover:shadow-lg active:scale-95"
            >
              Next Step <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleNext}
              disabled={loading}
              className="flex-1 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white font-bold py-3 px-6 rounded-xl transition-all flex items-center justify-center gap-2 hover:shadow-lg active:scale-95"
            >
              {loading ? (
                <><Loader2 className="w-5 h-5 animate-spin" /> Submitting...</>
              ) : (
                <><ChevronRight className="w-5 h-5" /> Continue to Payment</>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function IntakePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-green-600" />
      </div>
    }>
      <IntakeContent />
    </Suspense>
  );
}
