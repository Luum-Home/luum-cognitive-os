class CognitiveOs < Formula
  desc "Portable AI Agent Operating System — memory, quality gates, self-healing"
  homepage "https://github.com/luum-home/luum-cognitive-os"
  url "https://github.com/luum-home/luum-cognitive-os/archive/refs/tags/v0.1.0.tar.gz"
  # sha256 "UPDATE_WITH_ACTUAL_SHA256_AFTER_RELEASE"
  license "Apache-2.0"
  version "0.1.0"

  depends_on "bash"
  depends_on "git"

  def install
    # Install the CLI
    bin.install "bin/cognitive-os.sh" => "cognitive-os"

    # Install the framework files
    prefix.install ".cognitive-os"
    prefix.install "cognitive-os.yaml"
    prefix.install "install.sh"

    # Patch the CLI to find framework files in the Homebrew prefix
    inreplace bin/"cognitive-os", 'PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"', "PACKAGE_DIR=\"#{prefix}\""
  end

  test do
    system "#{bin}/cognitive-os", "version"
  end
end
