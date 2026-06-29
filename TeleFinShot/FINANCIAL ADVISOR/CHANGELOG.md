# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-02-28

### Changed
- **AI Interview Flow (Restructured):** Completely overhauled the `SYSTEM_INSTRUCTION` prompt in `services/gemini.ts` based on partner testing feedback.
  - The AI now asks **one question at a time** in a rapid-fire, back-and-forth conversational style instead of bundling multiple questions.
  - After completing **Stage 1 (Fixed Expenses)**, the AI presents a **mandatory recap** listing all expenses with a total and asks *"Want to change anything?"* before proceeding.
  - After completing **Stage 2 (Debts & Credit)**, the AI presents a **full accumulated recap** of income, expenses, and debts before moving to Stage 3.
  - Added new questions for **credit card limit** and **line of credit (LOC)** balance/interest rate.
  - Added a **Pro Plan teaser** at the end of Stage 4 — if the user has both a LOC and a higher-interest debt (e.g., car loan), the AI suggests how the Pro Plan could help them save.

### Added
- **New Data Fields:** Added `creditCardLimit`, `lineOfCreditBalance`, and `lineOfCreditInterestRate` to the `FinancialSnapshotData` interface.
- **Snapshot Display:** The Snapshot screen (`app/snapshot.tsx`) now displays Credit Card Limit and Line of Credit sections in the debts card.

### Updated
- **Chat Initial Message:** Updated the welcome message in `app/chat.tsx` to be more friendly and approachable.

## [Unreleased]

### Added (What we did so far)
- **Project Setup:** Initialized an Expo application (React Native) targeting Android and Web.
- **UI Framework:** Configured `react-native-paper` and established a custom Green/White/Black minimalist, pill-shaped design system across all screens.
- **AI Engine (Gemini):** Integrated Google's Gemini 2.5 Flash API (`services/gemini.ts`) to function as a financial assistant.
  - Configured prompt instructions to extract a 4-Stage Financial Profile (Income -> Debt -> Ecosystem -> Lifestyle).
  - Supported document (PDF/Image) parsing via Gemini so users can upload bills or statements.
  - Implemented error handling and sanitization to prevent JSON parse crashes (`U+0000 thru U+001F`).
- **User Authentication (Supabase):** Integrated Supabase Auth to securely manage user sessions (`providers/AuthProvider.tsx`).
  - Created elegant, fully-responsive `LoginScreen` and `SignupScreen` interfaces.
  - Established Route Guards (Global Layout interception) to restrict access to the core application unless logged in.
- **Welcome Screen Intelligence:** Overhauled the `index.tsx` screen to act dynamically based on Auth + AsyncStorage cache.
  - Displays Login/Signup for unauthenticated users.
  - Automatically un-locks "Resume My Snapshot" and "View Premium Insights" deep links if the user has an existing saved financial profile.
- **Superadmin Dashboard:** Implemented a secure Superadmin override via the `EXPO_PUBLIC_ADMIN_EMAILS` environment variable (supports a comma-separated list).
  - Provides a hidden "Admin Dashboard" button on the Welcome screen for the authorized superusers.
  - Introduces `app/admin.tsx` outlining global metrics and future platform manipulation hooks.
- **Chat Interface (`/chat`):** Built the conversational UI where users talk to the "Financial Snapshot" AI.
  - Added global persistence by binding the message state to a PostgreSQL database on Supabase (`conversations` table) avoiding data loss on crash or reinstall.
  - Added a "Restart Interview" action in the attachment menu.
  - Handled Android-specific Keyboard layouts dynamically using SafeArea margins to prevent layout squishing.
- **Snapshot Dashboard (`/snapshot`):** Implemented a dashboard that translates the AI's extracted JSON data into visual cards (Income, Expenses, Debt, Cash Flow).
- **Upsell Interface (`/upsell`):** Created a premium conversion screen offering the "Pro Plan" with personalized investment strategies and features.
- **User Profiles (Supabase Storage):** Allowed users to customize their display name and upload Avatar images natively.
  - Injected an automatic PostgreSQL trigger to map new users from `auth.users` into `public.profiles`.
- **Remote App Updating (OTA):** Integrated `expo-updates` so subsequent updates to the Android bundle are deployed over-the-air through EAS servers without regenerating Native `.apk` packages.

### Shipped (Completed)
- **End-to-End Testing:** Run through the entire flow (Chat -> extraction completion -> redirect to Snapshot -> redirect to Upsell) using real-world scenarios.
- **Android APK:** Built the standalone Android APK (two iterations, V2 includes the OTA update motor).

### Planned (What we will do next)
- **Teaser Value Logic:** Refine the calculation logic for the "Upsell Trigger" on the Snapshot screen (e.g., dynamically calculating "If you invested X, you'd yield Y% more").
- **UI/UX Polish:** Add micro-animations or improved transition states between the chat data collection and the final Snapshot render.
- **Web Deployment:** Prepare and deploy the web version of the application.
