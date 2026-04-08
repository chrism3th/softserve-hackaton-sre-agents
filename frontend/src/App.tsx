import { useState } from "react";
import { invokeAgent, listAgents } from "./api/client";

export default function App() {
  const [input, setInput] = useState("");
  const [output, setOutput] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [agent, setAgent] = useState("echo");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setOutput("");
    try {
      const res = await invokeAgent(agent, input);
      setOutput(res.output);
    } catch (err) {
      setOutput(`Error: ${(err as Error).message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container">
      <header>
        <h1>Next-Gen AI Agents</h1>
        <p className="tagline">Hackathon scaffold — backend + frontend + agents</p>
      </header>

      <form onSubmit={handleSubmit} className="card">
        <label htmlFor="agent">Agent</label>
        <select
          id="agent"
          value={agent}
          onChange={(e) => setAgent(e.target.value)}
        >
          <option value="echo">echo (smoke test)</option>
          <option value="claude">claude</option>
        </select>

        <label htmlFor="input">Input</label>
        <textarea
          id="input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask the agent anything..."
          rows={4}
          required
        />

        <button type="submit" disabled={loading || input.trim() === ""}>
          {loading ? "Thinking..." : "Invoke"}
        </button>
      </form>

      {output && (
        <section className="card output" aria-live="polite">
          <h2>Response</h2>
          <pre>{output}</pre>
        </section>
      )}
    </main>
  );
}
