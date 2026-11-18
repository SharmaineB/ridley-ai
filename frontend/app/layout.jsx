import '@fontsource-variable/inter';
import './globals.css';

export const metadata = {
  title: 'Ridley AI',
  description: 'IT support assistant for TaskUs teams',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
