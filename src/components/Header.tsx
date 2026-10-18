import Link from "next/link";
import { rubricLabels } from "@/lib/news";

export default function Header() {
  return (
    <header className="header">
      <Link href="/" className="logo">
        Development
      </Link>
      <nav className="nav">
        {Object.values(rubricLabels).map((label) => (
          <span key={label}>{label}</span>
        ))}
      </nav>
    </header>
  );
}
