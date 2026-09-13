def get_robot_stiffness_from_env(env):
    """
    Get robot joint stiffness/damping parameters from runtime environment
    Access through env.scene["robot"].data
    """
    print("🔍 Getting joint kp/kd parameters from runtime environment...")
    
    try:
        if not hasattr(env, 'scene'):
            print("❌ Environment has no 'scene' attribute")
            return None
        
        # Display available scene entities
        try:
            scene_keys = list(env.scene.keys()) if hasattr(env.scene, 'keys') else "Unable to get"
            print(f"📋 Available entities in scene: {scene_keys}")
        except:
            print("📋 Unable to get scene entity list")
            
        # Try to access robot object directly
        try:
            robot = env.scene["robot"]
            print(f"✅ Found robot object: {type(robot)}")
        except KeyError as e:
            print(f"❌ Cannot access robot object: {e}")
            return None
        
        if not hasattr(robot, 'data'):
            print("❌ Robot object has no 'data' attribute")
            return None
            
        robot_data = robot.data
        print(f"✅ Found robot.data object: {type(robot_data)}")
        
        # Explore all attributes in robot.data
        print("\n📊 Available attributes in robot.data:")
        print("-" * 60)
        
        data_attrs = [attr for attr in dir(robot_data) if not attr.startswith('_')]
        print(f"📈 Total attributes: {len(data_attrs)}")
        
        stiffness_attrs = []
        damping_attrs = []
        joint_attrs = []
        other_attrs = []
        
        for attr in data_attrs:
            if 'stiff' in attr.lower():
                stiffness_attrs.append(attr)
            elif 'damp' in attr.lower():
                damping_attrs.append(attr)
            elif 'joint' in attr.lower():
                joint_attrs.append(attr)
            else:
                other_attrs.append(attr)
        
        # Display joint-related attributes
        if joint_attrs:
            print(f"\n🔗 Joint-related attributes:")
            for attr in joint_attrs:
                try:
                    value = getattr(robot_data, attr)
                    print(f"   📌 {attr}: {type(value)} - shape: {getattr(value, 'shape', 'N/A')}")
                except Exception as e:
                    print(f"   📌 {attr}: Cannot access - {e}")
        
        # Display stiffness-related attributes
        if stiffness_attrs:
            print(f"\n💪 Stiffness-related attributes:")
            for attr in stiffness_attrs:
                try:
                    value = getattr(robot_data, attr)
                    print(f"   📌 {attr}: {type(value)} - shape: {getattr(value, 'shape', 'N/A')}")
                    if hasattr(value, 'shape') and len(value.shape) <= 2:
                        print(f"      Value: {value}")
                except Exception as e:
                    print(f"   📌 {attr}: Cannot access - {e}")
        
        # Display damping-related attributes
        if damping_attrs:
            print(f"\n🛠️ Damping-related attributes:")
            for attr in damping_attrs:
                try:
                    value = getattr(robot_data, attr)
                    print(f"   📌 {attr}: {type(value)} - shape: {getattr(value, 'shape', 'N/A')}")
                    if hasattr(value, 'shape') and len(value.shape) <= 2:
                        print(f"      Value: {value}")
                except Exception as e:
                    print(f"   📌 {attr}: Cannot access - {e}")
        
        # Display all potentially relevant attributes
        print(f"\n⚙️ All potentially relevant attributes (first 20):")
        control_keywords = ['default', 'joint', 'pos', 'vel', 'stiff', 'damp', 'kp', 'kd', 'control', 'target', 'limit']
        relevant_attrs = []
        
        for attr in data_attrs:
            if any(keyword in attr.lower() for keyword in control_keywords):
                relevant_attrs.append(attr)
        
        for attr in relevant_attrs[:20]:  # Show only first 20
            try:
                value = getattr(robot_data, attr)
                shape_info = getattr(value, 'shape', 'N/A')
                print(f"   📌 {attr}: {type(value).__name__} - shape: {shape_info}")
            except Exception as e:
                print(f"   📌 {attr}: Cannot access - {e}")
        
        if len(relevant_attrs) > 20:
            print(f"   ... {len(relevant_attrs) - 20} more relevant attributes")

        # Try common attribute names
        common_stiffness_names = [
            'default_joint_stiffness',
            'joint_stiffness', 
            'stiffness',
            'kp',
            'default_kp',
            'default_joint_pos_target',
            'joint_pos_target'
        ]
        
        common_damping_names = [
            'default_joint_damping',
            'joint_damping',
            'damping', 
            'kd',
            'default_kd',
            'default_joint_vel_target',
            'joint_vel_target'
        ]
        
        print(f"\n🔍 Trying common parameter names:")
        stiffness_found = None
        damping_found = None
        
        for name in common_stiffness_names:
            if hasattr(robot_data, name):
                try:
                    stiffness_found = getattr(robot_data, name)
                    print(f"   ✅ Found stiffness: {name}")
                    print(f"      Type: {type(stiffness_found)}")
                    print(f"      Shape: {getattr(stiffness_found, 'shape', 'N/A')}")
                    if hasattr(stiffness_found, 'shape') and len(stiffness_found.shape) <= 2:
                        print(f"      Value: {stiffness_found}")
                    break
                except Exception as e:
                    print(f"   ⚠️ {name} exists but cannot access: {e}")
        
        for name in common_damping_names:
            if hasattr(robot_data, name):
                try:
                    damping_found = getattr(robot_data, name)
                    print(f"   ✅ Found damping: {name}")
                    print(f"      Type: {type(damping_found)}")  
                    print(f"      Shape: {getattr(damping_found, 'shape', 'N/A')}")
                    if hasattr(damping_found, 'shape') and len(damping_found.shape) <= 2:
                        print(f"      Value: {damping_found}")
                    break
                except Exception as e:
                    print(f"   ⚠️ {name} exists but cannot access: {e}")
        
        # Check articulation object
        if hasattr(robot, 'articulation') and robot.articulation is not None:
            print(f"\n🔧 Checking articulation object:")
            articulation = robot.articulation
            print(f"   Type: {type(articulation)}")
            
            # Try articulation methods
            if hasattr(articulation, 'get_stiffnesses'):
                try:
                    artic_stiffness = articulation.get_stiffnesses()
                    print(f"   ✅ articulation.get_stiffnesses(): {artic_stiffness}")
                    if stiffness_found is None:
                        stiffness_found = artic_stiffness
                except Exception as e:
                    print(f"   ⚠️ get_stiffnesses() failed: {e}")
                    
            if hasattr(articulation, 'get_dampings'):
                try:
                    artic_damping = articulation.get_dampings()
                    print(f"   ✅ articulation.get_dampings(): {artic_damping}")
                    if damping_found is None:
                        damping_found = artic_damping
                except Exception as e:
                    print(f"   ⚠️ get_dampings() failed: {e}")
        
        # Return results
        result = {
            'stiffness': stiffness_found,
            'damping': damping_found,
            'robot_data': robot_data
        }
        
        print(f"\n✅ Parameter acquisition complete!")
        if stiffness_found is not None or damping_found is not None:
            print("🎉 Successfully found at least one parameter!")
        else:
            print("⚠️ No expected parameters found")
            
        return result
        
    except Exception as e:
        print(f"❌ Error getting parameters: {e}")
        import traceback
        traceback.print_exc()
        return None
