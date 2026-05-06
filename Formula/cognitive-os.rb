class CognitiveOs < Formula
  desc "Portable AI Agent Operating System — memory, quality gates, self-healing"
  homepage "https://github.com/luum-home/luum-cognitive-os"
  license "Apache-2.0"

  head "https://github.com/luum-home/luum-cognitive-os.git", branch: "main"

  depends_on "go" => :build
  depends_on "bash"
  depends_on "git"

  def install
    system "go", "build", "-ldflags", "-s -w", "-o", bin/"cos", "./cmd/cos"
    prefix.install "cognitive-os.yaml" if File.exist?("cognitive-os.yaml")
    prefix.install "scripts"
    prefix.install "hooks"
    prefix.install "rules"
    prefix.install "skills"
    prefix.install "templates" if File.directory?("templates")
  end

  test do
    system "#{bin}/cos", "version"
  end
end
