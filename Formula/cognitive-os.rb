class CognitiveOs < Formula
  desc "Portable AI Agent Operating System — memory, quality gates, self-healing"
  homepage "https://github.com/luum-home/luum-cognitive-os"
  # FSL-1.1-MIT is not in Homebrew's SPDX index (source-available, not OSI).
  # Converts automatically to MIT 2 years after first public release.
  # See: https://fsl.software and LICENSE at the root of this repository.
  license :cannot_represent

  head "https://github.com/luum-home/luum-cognitive-os.git", branch: "main"

  depends_on "go" => :build
  depends_on "bash"
  depends_on "git"

  def install
    cd "cmd/cos" do
      system "go", "build", "-ldflags", "-s -w", "-o", bin/"cos", "."
    end
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
