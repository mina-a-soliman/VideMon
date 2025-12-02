
#!/bin/bash
# fix_autotools.sh - Script to fix autotools issues in python-for-android builds

echo "=== Autotools Fix Script ==="
echo "This script patches common autotools issues in p4a dependencies"

# Function to patch configure.ac files
patch_configure_ac() {
    local file=$1
    echo "Patching: $file"
    
    # Check if file exists
    if [ ! -f "$file" ]; then
        echo "File not found: $file"
        return 1
    fi
    
    # Backup original file
    cp "$file" "${file}.backup"
    
    # Add m4_pattern_allow for common problematic macros
    cat > "${file}.tmp" << 'EOF'
m4_pattern_allow([LT_SYS_SYMBOL_USCORE])
m4_pattern_allow([AC_PROG_LIBTOOL])
m4_pattern_allow([AM_PROG_LIBTOOL])
m4_pattern_allow([LT_INIT])

EOF
    
    # Append original content
    cat "$file" >> "${file}.tmp"
    mv "${file}.tmp" "$file"
    
    echo "Patched successfully: $file"
    return 0
}

# Function to regenerate autotools files
regenerate_autotools() {
    local dir=$1
    echo "Regenerating autotools in: $dir"
    
    cd "$dir" || return 1
    
    # Run autoreconf to regenerate configure script
    if command -v autoreconf &> /dev/null; then
        echo "Running autoreconf..."
        autoreconf -fi 2>&1 | tee autoreconf.log
        
        if [ ${PIPESTATUS[0]} -eq 0 ]; then
            echo "✓ Autotools regenerated successfully"
            cd - > /dev/null
            return 0
        else
            echo "✗ Autoreconf failed, check autoreconf.log"
            cd - > /dev/null
            return 1
        fi
    else
        echo "✗ autoreconf not found"
        cd - > /dev/null
        return 1
    fi
}

# Main execution
echo ""
echo "Searching for problematic configure.ac files..."

# Search in buildozer directories
BUILDOZER_HOME="${HOME}/.buildozer"

if [ -d "$BUILDOZER_HOME" ]; then
    echo "Buildozer directory found: $BUILDOZER_HOME"
    
    # Find all configure.ac files in libffi directories
    while IFS= read -r -d '' file; do
        echo ""
        echo "Found: $file"
        
        # Check if file contains problematic macros
        if grep -q "LT_SYS_SYMBOL_USCORE\|AC_PROG_LIBTOOL\|AM_PROG_LIBTOOL" "$file" 2>/dev/null; then
            echo "Contains problematic macros, patching..."
            
            if patch_configure_ac "$file"; then
                # Get directory of configure.ac
                dir=$(dirname "$file")
                regenerate_autotools "$dir"
            fi
        else
            echo "No problematic macros found, skipping..."
        fi
    done < <(find "$BUILDOZER_HOME" -type f -name "configure.ac" -path "*/libffi*" -print0 2>/dev/null)
    
    # Also check for configure.in (older autotools)
    while IFS= read -r -d '' file; do
        echo ""
        echo "Found (configure.in): $file"
        
        if patch_configure_ac "$file"; then
            dir=$(dirname "$file")
            regenerate_autotools "$dir"
        fi
    done < <(find "$BUILDOZER_HOME" -type f -name "configure.in" -path "*/libffi*" -print0 2>/dev/null)
else
    echo "Buildozer directory not found yet. Run buildozer first, then this script."
fi

echo ""
echo "=== Script completed ==="
echo "If build still fails, check the autoreconf.log files for details."
