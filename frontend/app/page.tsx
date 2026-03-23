"use client";

import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Scale, Dumbbell, Heart, Activity, Trophy,
  Star, ChevronRight, Leaf, Mail, CheckCircle, ArrowRight, Zap
} from "lucide-react";

const GOALS = [
  {
    id: "lose_weight",
    title: "Lose Weight",
    subtitle: "Safe, sustainable fat loss",
    description: "Science-backed calorie deficit with balanced, locally appropriate meals. No crash diets.",
    icon: Scale,
    gradient: "from-orange-400 to-red-500",
    bg: "bg-orange-50",
    border: "border-orange-100",
    emoji: "🔥",
  },
  {
    id: "gain_muscle",
    title: "Gain Muscle",
    subtitle: "Lean muscle building",
    description: "High-protein diet optimized for muscle synthesis and strength.",
    icon: Dumbbell,
    gradient: "from-blue-500 to-indigo-600",
    bg: "bg-blue-50",
    border: "border-blue-100",
    emoji: "💪",
  },
  {
    id: "improve_health",
    title: "Improve Health",
    subtitle: "Whole-body wellness",
    description: "Micronutrient-rich, anti-inflammatory foods for long-term vitality.",
    icon: Heart,
    gradient: "from-pink-500 to-rose-600",
    bg: "bg-pink-50",
    border: "border-pink-100",
    emoji: "❤️",
  },
  {
    id: "medical_management",
    title: "Manage Diabetes / PCOS / Thyroid",
    subtitle: "Medical nutrition therapy",
    description: "Condition-specific diet plans backed by clinical nutrition guidelines and NutriVeda protocols.",
    icon: Activity,
    gradient: "from-purple-500 to-violet-600",
    bg: "bg-purple-50",
    border: "border-purple-100",
    emoji: "🩺",
  },
  {
    id: "sports_nutrition",
    title: "Sports Nutrition",
    subtitle: "Peak athletic performance",
    description: "Pre/post-workout nutrition, periodization, and recovery optimization.",
    icon: Trophy,
    gradient: "from-yellow-500 to-amber-600",
    bg: "bg-yellow-50",
    border: "border-yellow-100",
    emoji: "🏆",
  },
  {
    id: "maintain",
    title: "Maintain Weight",
    subtitle: "Stay fit and energetic",
    description: "Balanced macros and healthy habits to maintain your ideal physique.",
    icon: Leaf,
    gradient: "from-green-500 to-emerald-600",
    bg: "bg-green-50",
    border: "border-green-100",
    emoji: "🌿",
  },
  {
    id: "gain_muscle_lose_fat",
    title: "Gain Muscle & Lose Weight",
    subtitle: "Advanced body recomposition",
    description: "Build lean muscle while shedding fat simultaneously. Calories adjusted based on your target weight — surplus for mass gain, deficit for recomposition. High protein, consistent resistance training.",
    icon: Zap,
    gradient: "from-orange-500 to-amber-600",
    bg: "bg-orange-50",
    border: "border-orange-200",
    emoji: "⚡",
  },
];

const FEATURES = [
  { icon: "🧬", title: "BMR & TDEE Calculation", desc: "Precise calorie targets using the Mifflin-St Jeor equation" },
  { icon: "📚", title: "NutriVeda Knowledge Base", desc: "Plans grounded in certified nutrition diploma material and research" },
  { icon: "🌍", title: "Globally Tailored Food", desc: "Real local meals with exact portions — adapted to your city, country and cuisine" },
  { icon: "✅", title: "Nutritionist Approved", desc: "Every plan reviewed and approved before it reaches you" },
  { icon: "📄", title: "Personalised PDF Plan", desc: "Beautiful, printable weekly diet plan with full macro breakdown, emailed directly to you" },
  { icon: "💊", title: "Supplement Guidance", desc: "Evidence-based supplement recommendations when needed" },
];

const TESTIMONIALS = [
  { name: "Priya S.", goal: "Lost 12kg", text: "The plan was so practical! Real food I actually enjoy eating. Lost 12kg in 4 months.", stars: 5 },
  { name: "Rahul M.", goal: "Gained 8kg muscle", text: "High protein diet that actually works. My gym performance improved dramatically.", stars: 5 },
  { name: "Anita K.", goal: "PCOS management", text: "Finally a plan that understands PCOS! My hormonal symptoms reduced significantly.", stars: 5 },
];

export default function HomePage() {
  const router = useRouter();

  const handleGoalClick = (goalId: string) => {
    router.push(`/intake?goal=${goalId}`);
  };

  return (
    <div className="min-h-screen bg-white">
      {/* NAVBAR */}
      <nav className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-gray-100 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 bg-green-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-lg">🌿</span>
            </div>
            <div>
              <div className="font-bold text-gray-900 leading-none">NutriVeda</div>
              <div className="text-xs text-green-600 font-medium">Certified Nutritionist</div>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-6 text-sm font-medium text-gray-600">
            <a href="#goals" className="hover:text-green-600 transition-colors">Goals</a>
            <a href="#how-it-works" className="hover:text-green-600 transition-colors">How It Works</a>
            <a href="#testimonials" className="hover:text-green-600 transition-colors">Results</a>
          </div>
          <button
            onClick={() => router.push("/intake")}
            className="bg-green-600 hover:bg-green-700 text-white text-sm font-semibold px-5 py-2.5 rounded-xl transition-all hover:shadow-md active:scale-95"
          >
            Get My Plan →
          </button>
        </div>
      </nav>

      {/* HERO */}
      <section className="relative overflow-hidden bg-gradient-to-br from-green-50 via-white to-emerald-50 pt-16 pb-20">
        <div className="relative max-w-4xl mx-auto px-4 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 bg-green-100 text-green-800 text-sm font-semibold px-4 py-2 rounded-full mb-6">
              <span>🎓</span>
              <span>NutriVeda Certified Nutritionist — Diploma in Health & Body Nutrition</span>
            </div>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 leading-tight mb-6">
              Your Personalized
              <span className="text-green-600"> Diet & Fitness Plan </span>
              Awaits
            </h1>
            <p className="text-lg md:text-xl text-gray-600 max-w-2xl mx-auto mb-10 leading-relaxed">
              Science-backed nutrition plans using <strong>real, locally sourced food</strong>.
              BMR-calculated, NutriVeda-certified, and approved by your nutritionist before it reaches you.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={() => {
                  document.getElementById("goals")?.scrollIntoView({ behavior: "smooth" });
                }}
                className="bg-green-600 hover:bg-green-700 text-white font-bold px-8 py-4 rounded-2xl text-lg transition-all hover:shadow-xl active:scale-95 flex items-center justify-center gap-2"
              >
                Start My Assessment
                <ArrowRight className="w-5 h-5" />
              </button>
              <button
                onClick={() => router.push("/intake")}
                className="bg-white hover:bg-gray-50 text-gray-800 font-semibold px-8 py-4 rounded-2xl text-lg border-2 border-gray-200 transition-all hover:shadow-md"
              >
                Fill Intake Form
              </button>
            </div>
            <p className="text-sm text-gray-500 mt-4">
              Takes 5 minutes • Certified nutritionist reviewed • Personalised for you
            </p>
          </motion.div>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-14 grid grid-cols-3 gap-6 max-w-lg mx-auto"
          >
            {[
              { num: "100+", label: "Clients Helped" },
              { num: "MHB✓", label: "Certified" },
              { num: "Custom", label: "Meal Plans" },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-3xl font-bold text-green-600">{s.num}</div>
                <div className="text-sm text-gray-500 font-medium">{s.label}</div>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* GOAL CARDS */}
      <section id="goals" className="py-20 bg-gray-50">
        <div className="max-w-6xl mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              What&apos;s Your Goal?
            </h2>
            <p className="text-gray-500 text-lg max-w-xl mx-auto">
              Choose your goal to get a diet plan tailored exactly to your needs
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {GOALS.map((goal, i) => (
              <motion.div
                key={goal.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
                onClick={() => handleGoalClick(goal.id)}
                className={`cursor-pointer ${goal.bg} rounded-2xl p-6 border-2 ${goal.border} hover:shadow-xl transition-all duration-200 hover:-translate-y-1 group ${
                  goal.id === "gain_muscle_lose_fat"
                    ? "sm:col-span-2 lg:col-span-3 hover:border-orange-400"
                    : "hover:border-green-400"
                }`}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${goal.gradient} flex items-center justify-center text-white group-hover:scale-110 transition-transform`}>
                    <goal.icon className="w-6 h-6" />
                  </div>
                  {goal.id === "gain_muscle_lose_fat" && (
                    <span className="text-xs font-bold bg-orange-500 text-white px-3 py-1 rounded-full">
                      Advanced
                    </span>
                  )}
                </div>
                <div className="text-2xl mb-2">{goal.emoji}</div>
                <h3 className="text-xl font-bold text-gray-900 mb-1">{goal.title}</h3>
                <p className={`text-sm font-semibold mb-2 ${goal.id === "gain_muscle_lose_fat" ? "text-orange-600" : "text-green-600"}`}>
                  {goal.subtitle}
                </p>
                <p className="text-gray-600 text-sm leading-relaxed">{goal.description}</p>
                <div className={`mt-4 flex items-center font-semibold text-sm ${goal.id === "gain_muscle_lose_fat" ? "text-orange-600" : "text-green-600"}`}>
                  <span>Get my plan</span>
                  <ChevronRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" />
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how-it-works" className="py-20 bg-white">
        <div className="max-w-5xl mx-auto px-4">
          <div className="text-center mb-14">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">How It Works</h2>
            <p className="text-gray-500 text-lg">Simple, personalized, effective</p>
          </div>
          <div className="grid md:grid-cols-4 gap-8">
            {[
              { step: "1", title: "Fill the Form", desc: "5-step friendly intake form covering health, lifestyle, and food preferences", icon: "📝" },
              { step: "2", title: "Plan is Crafted", desc: "NutriVeda knowledge base and expert nutrition protocols build your personalized weekly meal plan", icon: "📋" },
              { step: "3", title: "Nutritionist Reviews", desc: "Your certified nutritionist reviews, edits, and approves the plan", icon: "✅" },
              { step: "4", title: "Plan Delivered", desc: "You receive a beautiful PDF diet plan via email", icon: "📧" },
            ].map((s, i) => (
              <motion.div
                key={s.step}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
                className="text-center"
              >
                <div className="w-16 h-16 bg-green-600 rounded-2xl flex items-center justify-center text-2xl mx-auto mb-4 shadow-lg shadow-green-200">
                  {s.icon}
                </div>
                <div className="text-xs font-bold text-green-600 mb-1">STEP {s.step}</div>
                <h3 className="font-bold text-gray-900 mb-2">{s.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{s.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section className="py-20 bg-green-600">
        <div className="max-w-5xl mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-white mb-3">
              Why Choose NutriVeda?
            </h2>
            <p className="text-green-200">Evidence-based, personalized, globally tailored</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 15 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.3, delay: i * 0.07 }}
                className="bg-white/10 backdrop-blur rounded-2xl p-6 border border-white/20"
              >
                <div className="text-3xl mb-3">{f.icon}</div>
                <h3 className="font-bold text-white mb-2">{f.title}</h3>
                <p className="text-green-100 text-sm leading-relaxed">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* TESTIMONIALS */}
      <section id="testimonials" className="py-20 bg-gray-50">
        <div className="max-w-5xl mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">Client Results</h2>
            <p className="text-gray-500">Real transformations, real food</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {TESTIMONIALS.map((t, i) => (
              <motion.div
                key={t.name}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
                className="bg-white rounded-2xl p-6 shadow-md border border-gray-100"
              >
                <div className="flex gap-1 mb-3">
                  {[...Array(t.stars)].map((_, j) => (
                    <Star key={j} className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                  ))}
                </div>
                <p className="text-gray-600 text-sm leading-relaxed mb-4 italic">&quot;{t.text}&quot;</p>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center text-green-700 font-bold">
                    {t.name[0]}
                  </div>
                  <div>
                    <div className="font-bold text-gray-900 text-sm">{t.name}</div>
                    <div className="text-green-600 text-xs font-semibold">{t.goal}</div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-gradient-to-br from-green-600 to-emerald-700">
        <div className="max-w-3xl mx-auto px-4 text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            Ready to Transform Your Health?
          </h2>
          <p className="text-green-100 text-lg mb-8 leading-relaxed">
            Fill out the 5-minute assessment and get a personalized, NutriVeda-certified
            nutrition plan tailored to your lifestyle and local food preferences.
          </p>
          <button
            onClick={() => router.push("/intake")}
            className="bg-white hover:bg-gray-50 text-green-700 font-bold px-10 py-4 rounded-2xl text-lg transition-all hover:shadow-xl active:scale-95 inline-flex items-center gap-2"
          >
            Start Your Assessment
            <ArrowRight className="w-5 h-5" />
          </button>
          <div className="flex items-center justify-center gap-6 mt-8 text-green-200 text-sm flex-wrap">
            <span className="flex items-center gap-1"><CheckCircle className="w-4 h-4" /> Expert-crafted plan</span>
            <span className="flex items-center gap-1"><CheckCircle className="w-4 h-4" /> Nutritionist reviewed</span>
            <span className="flex items-center gap-1"><CheckCircle className="w-4 h-4" /> Locally tailored food</span>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="bg-gray-900 text-gray-400 py-10">
        <div className="max-w-5xl mx-auto px-4 text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="w-8 h-8 bg-green-600 rounded-lg flex items-center justify-center">
              <span className="text-white">🌿</span>
            </div>
            <span className="text-white font-bold">NutriVeda Nutrition Consultation</span>
          </div>
          <p className="text-sm mb-4">
            Certified Nutritionist | Science-backed nutrition for real-world lifestyles
          </p>
          <div className="flex items-center justify-center gap-6 text-sm">
            <span className="flex items-center gap-1">
              <Mail className="w-4 h-4" /> nawinpauly3344@gmail.com
            </span>
          </div>
          <p className="text-xs mt-6 text-gray-600">
            © 2025 NutriVeda. All plans are for informational purposes.
            Consult your doctor for medical decisions.
          </p>
        </div>
      </footer>
    </div>
  );
}
