import { TopBar } from "@/components/top-bar";
import { PromptConsole } from "@/components/prompt-console";
import { ProjectList } from "@/components/project-list";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <TopBar />
      <main className="flex flex-1 flex-col px-6 pt-24 pb-16">
        <PromptConsole />
        <ProjectList />
      </main>
    </div>
  );
}
