import { Link } from 'react-router-dom';

export default function Home() {
  return (
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
      <div className="pt-8 space-y-6 width-full text-center">
        <p className="font-sans text-base text-muted-foreground">
          Built by students, for educators and researchers who believe grading should be fair.
        </p>
        <Link
          to="/courses"
          className="px-4 py-2.5 rounded-xl bg-foreground text-background font-medium hover:bg-opacity-90 transition"
        >
          Explore the platform
        </Link>
      </div>
    </main>
  );
}
