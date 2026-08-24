import { TopBar } from "@/components/top-bar";
import { PromptConsole } from "@/components/prompt-console";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <TopBar />
      <main className="flex flex-1 flex-col justify-center px-6 pb-24">
        <PromptConsole />
      </main>
    </div>
  );
}
