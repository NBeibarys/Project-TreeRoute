import Image from "next/image";
import Link from "next/link";

export function SiteBrand() {
  return (
    <Link className="brand-dock" href="/">
      <div className="brand-mark">
        <Image alt="treeroute logo" fill priority src="/treeroute-logo.jfif" />
      </div>
      <div className="brand-copy">
        <strong>treeroute</strong>
        <span>tree pollen-aware routing</span>
      </div>
    </Link>
  );
}
