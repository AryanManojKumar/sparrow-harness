import Nav from "@/components/sections/Nav";
import Hero from "@/components/sections/Hero";
import FeatureDetail from "@/components/sections/FeatureDetail";
import ProductShowcase from "@/components/sections/ProductShowcase";
import Footer from "@/components/sections/Footer";

export default function Home() {
  return (
    <main>
      <Nav />
      <Hero />
      <FeatureDetail />
      <ProductShowcase />
      <Footer />
    </main>
  );
}
