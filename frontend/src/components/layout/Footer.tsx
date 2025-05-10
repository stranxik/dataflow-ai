export default function Footer() {
  return (
    <footer className="bg-card shadow-sm mt-auto">
      <div className="container mx-auto px-4 py-4">
        <div className="flex flex-col md:flex-row justify-between items-center">
          <div className="text-sm text-muted-foreground">
            &copy; {new Date().getFullYear()} DataFlow AI. All rights reserved.
          </div>
          <div className="text-sm text-muted-foreground mt-2 md:mt-0">
            <a href="https://blaike.cc/" target="_blank" rel="noopener noreferrer" className="hover:text-primary transition-colors">
              blaike.cc
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
} 