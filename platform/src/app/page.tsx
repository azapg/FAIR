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
      <main className="container mx-auto p-6 space-y-12 pt-20">
        {/* Hero Section */}
        <div className="text-center space-y-6">
          <h1 className="font-serif text-4xl md:text-6xl font-bold text-foreground">
            The Future of Grading
          </h1>
          <p className="text-lg leading-relaxed text-foreground max-w-2xl mx-auto">
            FAIR helps educators design and automate the grading process using interpretable AI.
            From handwritten solutions to coding assignments, configure how grading works, or let FAIR handle it.
          </p>
        </div>

        {/* Optional CTA Section */}
        <div className="pt-8 space-y-4 width-full text-center">
          <p className="font-sans text-base text-muted-foreground">
            Built by students, for educators and researchers who believe grading should be fair.
          </p>
          <button className="px-6 py-3 rounded-2xl bg-foreground text-background font-medium hover:bg-opacity-90 transition">
            Explore the Docs
          </button>
        </div>

        {/* Typography Showcase */}
        <div className="border rounded-lg p-8 bg-card space-y-8">
          <div>
            <h2 className="font-serif text-3xl font-bold text-foreground mb-4">
              Typography System
            </h2>
            <p className="font-sans text-base text-muted-foreground">
              <strong>Headings:</strong> Remark (Serif) • <strong>Body:</strong> Host Grotesk (Sans-serif)
            </p>
          </div>

          {/* Heading Sizes */}
          <div className="space-y-4">
            <h1 className="font-serif text-4xl font-bold text-foreground">Heading 1 - Main Title</h1>
            <h2 className="font-serif text-3xl font-bold text-foreground">Heading 2 - Section Title</h2>
            <h3 className="font-serif text-2xl font-bold text-foreground">Heading 3 - Subsection</h3>
            <h4 className="font-serif text-xl font-semibold text-foreground">Heading 4 - Component Title</h4>
            <h5 className="font-serif text-lg font-semibold text-foreground">Heading 5 - Small Title</h5>
          </div>

          {/* Body Text Variations */}
          <div className="space-y-4">
            <p className="font-sans text-lg text-foreground">
              Large body text - Perfect for introductions and important information that needs emphasis.
            </p>
            <p className="font-sans text-base text-foreground">
              Regular body text - This is the standard text size for most content, comfortable for reading
              and providing a good balance between readability and space efficiency.
            </p>
            <p className="font-sans text-sm text-muted-foreground">
              Small body text - Ideal for captions, metadata, and secondary information that supports the main content.
            </p>
          </div>

          {/* Font Weights */}
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-serif text-lg font-semibold mb-3">Serif Weights (Remark)</h4>
              <div className="space-y-2">
                <p className="font-serif font-normal">Regular weight</p>
                <p className="font-serif font-bold">Bold weight</p>
                <p className="font-serif font-black">Black weight</p>
              </div>
            </div>
            <div>
              <h4 className="font-serif text-lg font-semibold mb-3">Sans Weights (Host Grotesk)</h4>
              <div className="space-y-2">
                <p className="font-sans font-light">Light weight</p>
                <p className="font-sans font-normal">Regular weight</p>
                <p className="font-sans font-medium">Medium weight</p>
                <p className="font-sans font-semibold">Semibold weight</p>
                <p className="font-sans font-bold">Bold weight</p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
