import { Violation, searchByPlate } from "../services/api";
import { FormEvent, useState } from "react";

interface Props {
  onResults: (items: Violation[]) => void;
}

export default function SearchBar({ onResults }: Props) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const data = await searchByPlate(query.trim());
      onResults(data.items);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="search-bar card" onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Search by license plate (e.g. DL01AB1234)"
        value={query}
        onChange={(e) => setQuery(e.target.value.toUpperCase())}
      />
      <button className="btn" type="submit" disabled={loading}>
        {loading ? "Searching..." : "Search"}
      </button>
    </form>
  );
}
