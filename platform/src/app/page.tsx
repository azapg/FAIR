import Header from "@/components/header";

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      <Header
        user={{
          name: "Allan Zapata",
          email: "allan.zapata@up.ac.pa",
          initials: "AZ",
        }}
      />
      <main className="container mx-auto p-6">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-4">Welcome to Fair Platform</h2>
          <p className="text-muted-foreground">Coruses go here...</p>
        </div>
      </main>
    </div>
  );
}
