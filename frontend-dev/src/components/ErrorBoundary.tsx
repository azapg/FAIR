// ErrorBoundary.tsx
import React, { Component, ErrorInfo, ReactNode } from "react";
import { toast } from "sonner";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(_: Error): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Show a toast notification instead of ugly error screen!
    toast.error("Something went wrong", {
      description: error.message,
      action: {
        label: "Reload",
        onClick: () => window.location.reload(),
      },
    });

    // Log to your error service
    console.error("Error caught:", error, errorInfo);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      // Show minimal fallback UI since toast already notified user
      return (
        <div style={{ padding: "20px", textAlign: "center" }}>
          <h2>Oops! Something went wrong</h2>
          <p>We've been notified and are looking into it.</p>
          <button onClick={() => window.location.reload()}>Reload Page</button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
