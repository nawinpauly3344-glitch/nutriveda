import type { Metadata, Viewport } from "next";
import { Toaster } from "react-hot-toast";
import "./globals.css";

export const metadata: Metadata = {
  title: "NutriVeda | Certified Nutritionist — Personalised Nutrition Plans",
  description:
    "Get a personalised diet and fitness plan from a certified NutriVeda nutritionist. Science-backed, locally tailored nutrition plans for weight loss, muscle gain, diabetes management, and more — for clients worldwide.",
  keywords: "nutritionist, diet plan, weight loss, muscle gain, NutriVeda, personalised meal plan, nutrition consultation, online nutritionist",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // Prevents iOS auto-zoom on form input focus (inputs already use 16px font)
  maximumScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <script src="https://checkout.razorpay.com/v1/checkout.js" async></script>
      </head>
      <body className="antialiased">
        {children}
        <Toaster
          position="top-center"
          toastOptions={{
            duration: 4000,
            style: { borderRadius: "12px", fontFamily: "inherit" },
            success: { iconTheme: { primary: "#16a34a", secondary: "white" } },
          }}
        />
      </body>
    </html>
  );
}
