// FILE LOCATION: frontend/src/components/common/ErrorBoundary.jsx
import { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error("Unhandled UI error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="m-6 rounded-lg border border-severity-critical/30 bg-severity-critical/10 p-6">
          <p className="font-mono text-sm text-severity-critical">
            This section failed to render: {this.state.error?.message || "unknown error"}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="mt-3 rounded border border-severity-critical/40 px-3 py-1.5 text-xs text-severity-critical hover:bg-severity-critical/10"
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
