"use client";

import Image from "next/image";
import Link from "next/link";

const ROUTES = [
  {
    name: "Gateway of India \u2013 Mandwa Jetty",
    slug: "gateway-mandwa",
    image: null,
    description:
      "The fastest sea route from Mumbai to Alibag. A ~45-minute AC catamaran ride from Gateway of India to Mandwa Jetty, followed by a free connecting bus to Alibag ST Stand.",
  },
];

const SERVICES = [
  {
    title: "Charter & Tourist Trips",
    subtitle: "Private Sailings Available",
    image: "/images/backgrounds/cruise-services.jpg",
    description:
      "PNP Maritime offers private catamaran charters for corporate events, family outings, and special occasions. Enjoy the scenic Mumbai harbour aboard our AC catamarans.",
    extra:
      "Advance booking required. Contact our Gateway of India office at 022-22884535 for charter enquiries and pricing.",
  },
  {
    title: "Port Operations",
    image: "/images/backgrounds/inland-services.jpg",
    description:
      "PNP also operates a multipurpose port at Dharamtar, Raigad, handling cargo including coal, steel coils, and cement.",
  },
];

export default function HomePage() {
  return (
    <div>
      {/* Hero Section */}
      <section className="relative bg-[#0c3547] overflow-hidden min-h-screen flex items-center">
        {/* Background Video */}
        <video
          autoPlay
          loop
          muted
          playsInline
          className="absolute inset-0 w-full h-full object-cover"
        >
          <source src="/videos/hero-bg.mp4" type="video/mp4" />
        </video>
        {/* Dark overlay for text readability */}
        <div className="absolute inset-0 bg-black/50" />

        <div className="relative max-w-7xl mx-auto px-4 py-24 md:py-32 text-center w-full">
          <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-sm px-4 py-2 rounded-full mb-6">
            <svg className="w-4 h-4 text-amber-400" fill="currentColor" viewBox="0 0 24 24">
              <path d="M20 21c-1.39 0-2.78-.47-4-1.32-2.44 1.71-5.56 1.71-8 0C6.78 20.53 5.39 21 4 21H2v-2h2c1.38 0 2.74-.35 4-.99 2.52 1.29 5.48 1.29 8 0 1.26.65 2.62.99 4 .99h2v2h-2zM3.95 19H4c1.6 0 3.02-.88 4-2 .98 1.12 2.4 2 4 2s3.02-.88 4-2c.98 1.12 2.4 2 4 2h.05l1.89-6.68c.08-.26.06-.54-.06-.78s-.34-.42-.6-.5L20 10.62V6c0-1.1-.9-2-2-2h-3V1H9v3H6c-1.1 0-2 .9-2 2v4.62l-1.29.42a1.007 1.007 0 00-.66 1.28L3.95 19zM6 6h12v3.97L12 8 6 9.97V6z" />
            </svg>
            <span className="text-white/90 text-sm font-medium">
              Mumbai&apos;s Premier Catamaran Service
            </span>
          </div>
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-4 leading-tight">
            Ready to Begin Your{" "}
            <span className="bg-gradient-to-r from-amber-400 via-orange-400 to-amber-500 bg-clip-text text-transparent">
              Journey
            </span>
            ?
          </h1>
          <p className="text-lg text-gray-300 max-w-2xl mx-auto mb-8 leading-relaxed">
            Experience fast catamaran travel from Gateway of India to Mandwa Jetty.
            AC and non-AC seating available. Includes free bus to Alibag.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link
              href="/customer/login"
              className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white px-8 py-3 rounded-lg text-base font-semibold transition-all shadow-lg hover:shadow-xl hover:scale-105"
            >
              Book Your Ferry
            </Link>
            <Link
              href="#routes"
              className="border-2 border-white/30 hover:border-white/60 text-white px-8 py-3 rounded-lg text-base font-semibold transition-all hover:bg-white/10"
            >
              View Routes
            </Link>
          </div>
          <p className="text-gray-400 text-sm mt-12 animate-bounce">
            Scroll to explore
          </p>
        </div>
      </section>

      {/* Ferry Routes Section */}
      <section id="routes" className="py-16 md:py-20 bg-gradient-to-b from-white to-sky-50">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-12">
            <span className="inline-block text-sky-600 bg-sky-50 text-xs font-bold tracking-wider uppercase px-4 py-1.5 rounded-full mb-3">
              Our Routes
            </span>
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">
              Ferry Services
            </h2>
            <p className="text-gray-500 max-w-2xl mx-auto">
              Connecting Mumbai to Alibag with fast, comfortable catamaran service since 1999.
            </p>
          </div>

          {/* First row: 3 cards */}
          <div className="grid grid-cols-1 gap-6 mb-6 max-w-lg mx-auto">
            {ROUTES.slice(0, 3).map((route) => (
              <div
                key={route.name}
                className="group bg-white rounded-xl shadow-md hover:shadow-xl transition-all duration-300 overflow-hidden border border-gray-100"
              >
                <div className="relative h-48 overflow-hidden bg-gradient-to-br from-[#0c3547] to-[#1a6b8a]">
                  {route.image ? (
                    <Image
                      src={route.image}
                      alt={route.name}
                      fill
                      sizes="(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 33vw"
                      className="object-cover group-hover:scale-105 transition-transform duration-500"
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <svg className="w-16 h-16 text-white/20" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M20 21c-1.39 0-2.78-.47-4-1.32-2.44 1.71-5.56 1.71-8 0C6.78 20.53 5.39 21 4 21H2v-2h2c1.38 0 2.74-.35 4-.99 2.52 1.29 5.48 1.29 8 0 1.26.65 2.62.99 4 .99h2v2h-2zM3.95 19H4c1.6 0 3.02-.88 4-2 .98 1.12 2.4 2 4 2s3.02-.88 4-2c.98 1.12 2.4 2 4 2h.05l1.89-6.68c.08-.26.06-.54-.06-.78s-.34-.42-.6-.5L20 10.62V6c0-1.1-.9-2-2-2h-3V1H9v3H6c-1.1 0-2 .9-2 2v4.62l-1.29.42a1.007 1.007 0 00-.66 1.28L3.95 19zM6 6h12v3.97L12 8 6 9.97V6z" />
                      </svg>
                    </div>
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />
                  {"status" in route && route.status === "closed" && (
                    <span className="absolute top-3 right-3 bg-red-500 text-white text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-full">
                      Closed
                    </span>
                  )}
                  <div className="absolute bottom-3 left-3">
                    <span className="bg-gradient-to-r from-amber-500 to-orange-500 text-white text-xs font-bold px-3 py-1 rounded-full">
                      {route.name}
                    </span>
                  </div>
                </div>
                <div className="p-5">
                  <h3 className="text-lg font-bold text-slate-900 mb-2">
                    {route.name}
                  </h3>
                  <p className="text-gray-500 text-sm leading-relaxed mb-3">
                    {route.description}
                  </p>
                  <Link
                    href={`/route/${route.slug}`}
                    className="text-sky-600 text-sm font-semibold hover:text-sky-800 transition-colors"
                  >
                    Know More &rarr;
                  </Link>
                </div>
              </div>
            ))}
          </div>

        </div>
      </section>

      {/* Our Other Services — Featured layout */}
      <section className="py-16 md:py-20 bg-sky-50">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-12">
            <span className="inline-block text-amber-700 bg-amber-50 text-xs font-bold tracking-wider uppercase px-4 py-1.5 rounded-full border border-amber-200 mb-3">
              What We Offer
            </span>
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">
              Our Other Services
            </h2>
          </div>

          {/* Featured: Cruise Service — full-width horizontal card */}
          <div className="bg-white rounded-2xl overflow-hidden shadow-lg hover:shadow-2xl transition-all duration-300 mb-8">
            <div className="grid grid-cols-1 lg:grid-cols-2">
              <div className="relative h-64 lg:h-auto lg:min-h-[380px]">
                <Image
                  src={SERVICES[0].image}
                  alt={SERVICES[0].title}
                  fill
                  sizes="(max-width: 1024px) 100vw, 50vw"
                  className="object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-r from-black/20 to-transparent lg:bg-none" />
              </div>
              <div className="p-8 lg:p-10 flex flex-col justify-center">
                <span className="inline-block text-amber-600 bg-amber-50 text-xs font-bold tracking-wider uppercase px-3 py-1 rounded-full border border-amber-200 w-fit mb-4">
                  Featured
                </span>
                <h3 className="text-2xl lg:text-3xl font-bold text-slate-900 mb-2">
                  {SERVICES[0].title}
                </h3>
                {SERVICES[0].subtitle && (
                  <p className="text-amber-500 font-semibold mb-4">{SERVICES[0].subtitle}</p>
                )}
                <p className="text-gray-600 leading-relaxed mb-4">
                  {SERVICES[0].description}
                </p>
                {SERVICES[0].extra && (
                  <p className="text-gray-500 text-sm leading-relaxed">
                    {SERVICES[0].extra}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Secondary services: 2-column */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {SERVICES.slice(1).map((service) => (
              <div
                key={service.title}
                className="group bg-white rounded-2xl overflow-hidden shadow-lg hover:shadow-2xl transition-all duration-300"
              >
                <div className="relative h-52">
                  <Image
                    src={service.image}
                    alt={service.title}
                    fill
                    sizes="(max-width: 768px) 100vw, 50vw"
                    className="object-cover group-hover:scale-105 transition-transform duration-500"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                  <div className="absolute bottom-0 left-0 right-0 p-5">
                    <h3 className="text-xl font-bold text-white">{service.title}</h3>
                  </div>
                </div>
                <div className="p-6">
                  <p className="text-gray-600 text-sm leading-relaxed">
                    {service.description}
                  </p>
                  {"extra" in service && service.extra && (
                    <p className="text-gray-500 text-sm leading-relaxed mt-3">
                      {service.extra}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Why Choose Us — 2-column: bullet points + stats */}
      <section className="py-16 md:py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
            {/* Left: Text with bullet points */}
            <div>
              <span className="inline-block text-sky-600 bg-sky-50 text-xs font-bold tracking-wider uppercase px-4 py-1.5 rounded-full mb-4">
                Why Choose Us
              </span>
              <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-3">
                Why Thousands Trust Us
              </h2>
              <p className="text-gray-500 mb-8 leading-relaxed">
                The trusted choice for ferry travel across Maharashtra&apos;s Konkan coast.
              </p>

              <div className="space-y-5">
                {[
                  {
                    title: "Safe & Reliable",
                    text: "All catamarans meet Maharashtra Maritime Board safety standards",
                  },
                  {
                    title: "On-Time Service",
                    text: "7 daily sailings each direction, 365 days a year",
                  },
                  {
                    title: "AC Catamaran",
                    text: "The only AC catamaran service on the Gateway\u2013Mandwa route",
                  },
                  {
                    title: "Since 1999",
                    text: "Over 25 years serving Mumbai\u2013Alibag travellers",
                  },
                ].map((item) => (
                  <div key={item.title} className="flex gap-4">
                    <div className="flex-shrink-0 w-6 h-6 mt-0.5 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center">
                      <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-900">{item.title}</h3>
                      <p className="text-gray-500 text-sm mt-0.5">{item.text}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Right: Stats in a 2x2 grid */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gradient-to-br from-[#0c3547] to-[#1a6b8a] rounded-2xl p-6 md:p-8 text-center">
                <div className="text-3xl md:text-4xl font-bold text-amber-400 mb-1">25+</div>
                <div className="text-gray-300 text-sm">Years of Service</div>
              </div>
              <div className="bg-gradient-to-br from-[#0f3a50] to-[#1a5c7a] rounded-2xl p-6 md:p-8 text-center">
                <div className="text-3xl md:text-4xl font-bold text-amber-400 mb-1">1</div>
                <div className="text-gray-300 text-sm">Active Route</div>
              </div>
              <div className="bg-gradient-to-br from-[#0f3a50] to-[#1a5c7a] rounded-2xl p-6 md:p-8 text-center">
                <div className="text-3xl md:text-4xl font-bold text-amber-400 mb-1">350+</div>
                <div className="text-gray-300 text-sm">Passengers Per Sailing</div>
              </div>
              <div className="bg-gradient-to-br from-[#0c3547] to-[#1a6b8a] rounded-2xl p-6 md:p-8 text-center">
                <div className="text-3xl md:text-4xl font-bold text-amber-400 mb-1">1M+</div>
                <div className="text-gray-300 text-sm">Passengers Served</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* About Section - Dark Navy Gradient Background */}
      <section className="py-16 md:py-20 bg-gradient-to-br from-[#1a5c7a] via-[#0f3a50] to-[#0a2030]">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-8">
            <span className="inline-block text-cyan-300 bg-white/10 text-xs font-bold tracking-wider uppercase px-4 py-1.5 rounded-full mb-3">
              About Us
            </span>
            <h2 className="text-3xl md:text-4xl font-bold text-white">
              About PNP Maritime
            </h2>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
            {/* Image — no floating badge */}
            <div className="relative">
              <div className="relative w-full h-80 md:h-96 rounded-2xl overflow-hidden shadow-2xl ring-2 ring-white/10">
                <Image
                  src="/images/general/team-photo.jpg"
                  alt="Our Leadership"
                  fill
                  sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 600px"
                  className="object-cover"
                />
              </div>
            </div>

            {/* Content — slightly more compact */}
            <div>
              <p className="text-gray-300 leading-relaxed mb-3">
                PNP Maritime Services Pvt. Ltd. has been connecting Mumbai to the Konkan coast since 1999. We operate the only air-conditioned catamaran service on the Gateway of India to Mandwa Jetty route.
              </p>
              <p className="text-gray-300 leading-relaxed mb-3">
                Our catamarans accommodate over 350 passengers per sailing across two seating options &mdash; Main Deck and AC Deck. All vessels are approved by the Maharashtra Maritime Board and undergo annual safety inspections.
              </p>
              <p className="text-gray-300 leading-relaxed mb-5">
                Every sailing includes a complimentary connecting bus service from Mandwa Jetty to Alibag ST Stand, making the complete Mumbai&ndash;Alibag journey seamlessly connected in under 2 hours.
              </p>

              <div className="flex flex-wrap gap-4 mb-5">
                <div className="flex items-center gap-2 bg-white/10 px-4 py-2 rounded-lg">
                  <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-sm font-medium text-white">350+ Capacity</span>
                </div>
                <div className="flex items-center gap-2 bg-white/10 px-4 py-2 rounded-lg">
                  <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-sm font-medium text-white">1 Active Route</span>
                </div>
                <div className="flex items-center gap-2 bg-white/10 px-4 py-2 rounded-lg">
                  <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-sm font-medium text-white">Daily Service</span>
                </div>
              </div>

              <Link
                href="/about"
                className="inline-flex items-center gap-2 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white px-6 py-3 rounded-lg font-semibold transition-all shadow-lg hover:shadow-xl"
              >
                Learn More About Us
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
