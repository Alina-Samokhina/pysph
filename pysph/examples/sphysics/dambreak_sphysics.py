"""Dam break past an obstacle with data from SPHysics. (40 minutes)

For benchmarking, we use the input geometry and discretization as the
SPHYSICS Case 5
(https://wiki.manchester.ac.uk/sphysics/index.php/SPHYSICS_Home_Page)

We only require the INDAT and IPART files generated by SPHysics. These
define respectively, the numerical parameters and the initial particle
data used for the run. The rest of the problem is set-up in the usual
way.

"""
import os
import numpy

from pysph.sph.equation import Group
from pysph.base.kernels import CubicSpline
from pysph.sph.wc.basic import TaitEOS, TaitEOSHGCorrection, MomentumEquation
from pysph.sph.basic_equations import ContinuityEquation, XSPHCorrection

from pysph.solver.solver import Solver
from pysph.solver.application import Application
from pysph.sph.integrator import EPECIntegrator, PECIntegrator
from pysph.sph.integrator_step import WCSPHStep

from pysph.tools.sphysics import sphysics2pysph

MY_DIR = os.path.dirname(__file__)
INDAT = os.path.join(MY_DIR, 'INDAT.gz')
IPART = os.path.join(MY_DIR, 'IPART.gz')

# problem dimensionality
dim = 3

# suggested initial time step and final time
dt = 1e-5
tf = 2.0

# physical constants for the run loaded from SPHysics INDAT
indat = numpy.loadtxt(INDAT)
H = float( indat[10] )
B = float( indat[11] )
gamma = float( indat[12] )
eps = float( indat[14] )
rho0 = float( indat[15] )
alpha = float( indat[16] )
beta = 0.0
c0 = numpy.sqrt( B*gamma/rho0 )

class DamBreak3DSPhysics(Application):
    def add_user_options(self, group):
        group.add_argument(
            "--test", action="store_true", dest="test", default=False,
            help="For use while testing of results, uses PEC integrator."
        )

    def create_particles(self):
         return sphysics2pysph(IPART, INDAT, vtk=False)

    def create_solver(self):
        kernel = CubicSpline(dim=3)

        if self.options.test:
            integrator = PECIntegrator(fluid=WCSPHStep(),boundary=WCSPHStep())
            adaptive, n_damp = False, 0
        else:
            integrator = EPECIntegrator(fluid=WCSPHStep(),boundary=WCSPHStep())
            adaptive, n_damp = True, 0

        solver = Solver(dim=dim, kernel=kernel, integrator=integrator,
                        adaptive_timestep=adaptive, tf=tf, dt=dt,
                        n_damp=n_damp)
        return solver

    def create_equations(self):
        equations = [

            # Equation of state
            Group(equations=[
                    TaitEOS(dest='fluid', sources=None,
                            rho0=rho0, c0=c0, gamma=gamma),
                    TaitEOSHGCorrection(dest='boundary', sources=None,
                                        rho0=rho0, c0=c0, gamma=gamma),

                    ], real=False),

            # Continuity Momentum and XSPH equations
            Group(equations=[
                    ContinuityEquation(dest='fluid',
                                       sources=['fluid', 'boundary']),
                    ContinuityEquation(dest='boundary', sources=['fluid']),

                    MomentumEquation(
                        dest='fluid', sources=['fluid', 'boundary'], c0=c0,
                        alpha=alpha, beta=beta, gz=-9.81,
                        tensile_correction=True),

                       # Position step with XSPH
                    XSPHCorrection(dest='fluid', sources=['fluid'], eps=eps)
                 ])
            ]
        return equations

if __name__ == '__main__':
    app = DamBreak3DSPhysics()
    app.run()
