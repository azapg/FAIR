import localFont from "next/font/local";

// Host Grotesk for body text (sans-serif)
export const hostGrotesk = localFont({
  src: [
    {
      path: "../../public/fonts/host-grotesk/HostGrotesk-Light.ttf",
      weight: "300",
      style: "normal",
    },
    {
      path: "../../public/fonts/host-grotesk/HostGrotesk-Regular.ttf",
      weight: "400",
      style: "normal",
    },
    {
      path: "../../public/fonts/host-grotesk/HostGrotesk-Medium.ttf",
      weight: "500",
      style: "normal",
    },
    {
      path: "../../public/fonts/host-grotesk/HostGrotesk-SemiBold.ttf",
      weight: "600",
      style: "normal",
    },
    {
      path: "../../public/fonts/host-grotesk/HostGrotesk-Bold.ttf",
      weight: "700",
      style: "normal",
    },
  ],
  variable: "--font-host-grotesk",
  display: "swap",
});

// Remark for headings (serif)
export const remark = localFont({
  src: [
    {
      path: "../../public/fonts/remark/LTRemark-Regular.otf",
      weight: "400",
      style: "normal",
    },
    {
      path: "../../public/fonts/remark/LTRemark-Bold.otf",
      weight: "700",
      style: "normal",
    },
    {
      path: "../../public/fonts/remark/LTRemark-Black.otf",
      weight: "900",
      style: "normal",
    },
  ],
  variable: "--font-remark",
  display: "swap",
});
