class KimaiCli < Formula
  include Language::Python::Virtualenv

  desc "CLI for Kimai time tracking software"
  homepage "https://github.com/ksassnowski/kimai-cli"
  url "https://github.com/ksassnowski/kimai-cli/releases/download/0.2.0/kimai-cli-0.2.0.tar.gz"
  sha256 "785b5d68bb431d3940c720d542332dfa7af2173a4e6e0e4ef3bc54b8968fd820"

  depends_on "python"

  def install
    venv = virtualenv_create(libexec, "python3")
    system libexec/"bin/pip", "install", "-v", "--no-binary", ":all:",
                              "--ignore-installed", buildpath
    system libexec/"bin/pip", "uninstall", "-y", "kimai-cli"
    venv.pip_install_and_link buildpath
  end

  test do
    system "false"
  end
end
