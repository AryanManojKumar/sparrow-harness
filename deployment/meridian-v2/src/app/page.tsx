import Nav from "@/components/sections/Nav";
import Hero from "@/components/sections/Hero";
import ProductShowcase from "@/components/sections/ProductShowcase";
import FeatureDetail from "@/components/sections/FeatureDetail";
import Cta from "@/components/sections/Cta";
import Testimonial from "@/components/sections/Testimonial";
import Footer from "@/components/sections/Footer";

export default function Home() {
  return (
    <main>
      <Nav />
      <Hero />
      <ProductShowcase />
      <FeatureDetail />
      <Cta />
      <Testimonial />
      <Footer />
    </main>
  );
}
