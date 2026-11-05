#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WinePrefix {
    pub path: String,
    pub arch: String, // win32 or win64
}

impl WinePrefix {
    pub fn default_prefix() -> Self {
        Self { path: "~/.wine".into(), arch: "win64".into() }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn test_wine_prefix_aaa() {
        // Arrange & Act
        let prefix = WinePrefix::default_prefix();
        // Assert
        assert_eq!(prefix.arch, "win64");
    }
}
