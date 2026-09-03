import { TopBar } from "@/components/top-bar";
import { PromptConsole } from "@/components/prompt-console";
import { ProjectList } from "@/components/project-list";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <TopBar />
      {/* The console stays the hero — centred in the first screenful with the
          sparrow above it. Past work sits below the fold, found by scrolling,
          so it never competes with the empty prompt box on arrival. */}
      <main className="flex flex-1 flex-col px-6 pb-24">
        <div className="flex min-h-[78vh] flex-col justify-center">
          <PromptConsole />
        </div>
        <ProjectList />
      </main>
    </div>
  );
}
